"""Authenticated one-to-one history plus Channels delivery, with replay-safe tickets."""
import hashlib
import logging
import secrets
from datetime import timedelta
from asgiref.sync import async_to_sync, sync_to_async
from bson import ObjectId
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.core.cache import cache
from pymongo.errors import DuplicateKeyError
from rest_framework.exceptions import NotFound, PermissionDenied, Throttled, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from urllib.parse import parse_qs
from .authentication import session_is_active
from .common import now, object_id, pair_key
from .mongo import get_collection
from .people import are_connected
from .serializers import ConversationSerializer, MessageSerializer

logger = logging.getLogger(__name__)

def conversation_group(identifier):
    return f"conversation_{identifier}"

def allowed_conversation(user_id, conversation_id):
    conversation = get_collection("conversations").find_one({"_id": conversation_id, "participants": user_id})
    if conversation is None:
        return None
    other = next((p for p in conversation["participants"] if p != user_id), None)
    return conversation if other and are_connected(user_id, other) else None

def message_data(message):
    return {"id": str(message["_id"]), "conversation_id": str(message["conversation_id"]), "sender_id": str(message["sender_id"]), "content": message["content"], "client_id": message.get("client_id"), "created_at": message["created_at"].isoformat(), "read_by": [str(u) for u in message.get("read_by", [])]}

def publish(conversation_id, event):
    try:
        async_to_sync(get_channel_layer().group_send)(conversation_group(conversation_id), event)
    except Exception:
        # History is durable even during a channel-layer outage; reconnect reloads it.
        logger.exception("Live delivery failed; message/history remains in MongoDB.")

def persist_message(conversation_id, sender_id, content, client_id):
    conversation_id, sender_id = object_id(conversation_id), object_id(sender_id)
    if not allowed_conversation(sender_id, conversation_id):
        raise PermissionDenied("Connect with this student before messaging.")
    duplicate = get_collection("messages").find_one({"conversation_id": conversation_id, "sender_id": sender_id, "client_id": str(client_id)})
    if duplicate:
        return message_data(duplicate)
    key = f"message-rate:{sender_id}"
    if cache.add(key, 1, timeout=60):
        count = 1
    else:
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=60)
            count = 1
    if count > 60:
        raise Throttled(detail="Please wait before sending more messages.")
    row = {"conversation_id": conversation_id, "sender_id": sender_id, "content": content, "client_id": str(client_id), "created_at": now(), "read_by": [sender_id]}
    try:
        row["_id"] = get_collection("messages").insert_one(row).inserted_id
    except DuplicateKeyError:
        row = get_collection("messages").find_one({"conversation_id": conversation_id, "sender_id": sender_id, "client_id": str(client_id)})
    get_collection("conversations").update_one({"_id": conversation_id}, {"$set": {"last_message": content, "updated_at": now()}})
    payload = message_data(row)
    publish(str(conversation_id), {"type": "chat.message", "message": payload})
    return payload

class ConversationsView(APIView):
    def get(self, request):
        actor = ObjectId(request.user.id)
        result = []
        for conversation in get_collection("conversations").find({"participants": actor}).sort("updated_at", -1).limit(100):
            if not allowed_conversation(actor, conversation["_id"]):
                continue
            other = next(p for p in conversation["participants"] if p != actor)
            user = get_collection("users").find_one({"_id": other})
            unread = get_collection("messages").count_documents({"conversation_id": conversation["_id"], "sender_id": {"$ne": actor}, "read_by": {"$ne": actor}})
            result.append({"id": str(conversation["_id"]), "participant_id": str(other), "participant_name": user["name"] if user else "Student", "last_message": conversation.get("last_message", ""), "updated_at": conversation["updated_at"], "unread_count": unread})
        return Response({"items": result})

    def post(self, request):
        serializer = ConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor, recipient = ObjectId(request.user.id), object_id(serializer.validated_data["recipient_id"])
        if actor == recipient or not are_connected(actor, recipient):
            raise PermissionDenied("You can message after a connection request is accepted.")
        key = pair_key(actor, recipient)
        collection = get_collection("conversations")
        row = collection.find_one({"pair_key": key})
        if row:
            return Response({"id": str(row["_id"]), "created": False})
        try:
            identifier = collection.insert_one({"pair_key": key, "participants": sorted([actor, recipient], key=str), "created_at": now(), "updated_at": now(), "last_message": ""}).inserted_id
        except DuplicateKeyError:
            identifier = collection.find_one({"pair_key": key})["_id"]
        return Response({"id": str(identifier), "created": True}, status=201)

class ConversationMessagesView(APIView):
    def get_conversation(self, request, conversation_id):
        conversation = allowed_conversation(ObjectId(request.user.id), object_id(conversation_id))
        if conversation is None:
            raise NotFound("Conversation not found.")
        return conversation

    def get(self, request, conversation_id):
        conversation = self.get_conversation(request, conversation_id)
        query = {"conversation_id": conversation["_id"]}
        before, after = request.query_params.get("before"), request.query_params.get("after")
        if before and after:
            raise ValidationError("Use either before or after.")
        if before or after:
            query["_id"] = {"$lt" if before else "$gt": object_id(before or after)}
        rows = list(get_collection("messages").find(query).sort("_id", 1 if after else -1).limit(51))
        more = len(rows) > 50
        rows = rows[:50]
        if not after:
            rows.reverse()
        return Response({"items": [message_data(row) for row in rows], "has_more": more, "cursor": str(rows[-1 if after else 0]["_id"]) if rows else None})

    def post(self, request, conversation_id):
        self.get_conversation(request, conversation_id)
        serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(persist_message(conversation_id, request.user.id, **serializer.validated_data), status=201)

    def patch(self, request, conversation_id):
        conversation = self.get_conversation(request, conversation_id)
        actor = ObjectId(request.user.id)
        through = object_id(request.data.get("through"))
        get_collection("messages").update_many({"conversation_id": conversation["_id"], "sender_id": {"$ne": actor}, "_id": {"$lte": through}}, {"$addToSet": {"read_by": actor}})
        publish(conversation_id, {"type": "chat.read", "reader_id": request.user.id, "through": str(through)})
        return Response({"status": "read"})

class WebSocketTicketView(APIView):
    def post(self, request, conversation_id):
        actor, identifier = ObjectId(request.user.id), object_id(conversation_id)
        if not allowed_conversation(actor, identifier):
            raise NotFound("Conversation not found.")
        ticket = secrets.token_urlsafe(32)
        get_collection("websocket_tickets").insert_one({"ticket_hash": hashlib.sha256(ticket.encode()).hexdigest(), "user_id": actor, "session_id": request.user.session_id, "conversation_id": identifier, "expires_at": now() + timedelta(seconds=60)})
        return Response({"ticket": ticket, "expires_in": 60})

class ConversationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        query = parse_qs(self.scope.get("query_string", b"").decode("ascii", errors="ignore"))
        ticket = query.get("ticket", [""])[0]
        record = await sync_to_async(self.consume_ticket, thread_sensitive=False)(ticket, self.conversation_id)
        if record is None:
            await self.close(code=4401)
            return
        self.user_id, self.session_id = str(record["user_id"]), record["session_id"]
        self.group_name = conversation_group(self.conversation_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    @staticmethod
    def consume_ticket(ticket, conversation_id):
        record = get_collection("websocket_tickets").find_one_and_delete({"ticket_hash": hashlib.sha256(ticket.encode()).hexdigest(), "conversation_id": ObjectId(conversation_id), "expires_at": {"$gt": now()}})
        if record and session_is_active(record["user_id"], record["session_id"]) and allowed_conversation(record["user_id"], ObjectId(conversation_id)):
            return record
        return None

    async def authorized(self):
        def check():
            actor = ObjectId(self.user_id)
            return session_is_active(actor, self.session_id) and allowed_conversation(actor, ObjectId(self.conversation_id)) is not None
        return await sync_to_async(check, thread_sensitive=False)()

    async def disconnect(self, close_code):
        if getattr(self, "group_name", None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if not await self.authorized():
            await self.close(code=4403)
            return
        if not isinstance(content, dict):
            await self.send_json({"type": "error", "detail": "Send a JSON object."})
            return
        serializer = MessageSerializer(data=content)
        if not serializer.is_valid():
            await self.send_json({"type": "error", "errors": serializer.errors})
            return
        try:
            message = await sync_to_async(persist_message, thread_sensitive=False)(self.conversation_id, self.user_id, **serializer.validated_data)
            await self.send_json({"type": "sent", "message_id": message["id"]})
        except (PermissionDenied, Throttled) as error:
            await self.send_json({"type": "error", "detail": str(error.detail)})

    async def chat_message(self, event):
        if await self.authorized():
            await self.send_json({"type": "message", "message": event["message"]})
        else:
            await self.close(code=4403)

    async def chat_read(self, event):
        if await self.authorized():
            await self.send_json({"type": "read", "reader_id": event["reader_id"], "through": event["through"]})
