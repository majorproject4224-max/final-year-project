import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from asgiref.sync import async_to_sync, sync_to_async
from bson import ObjectId
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from pymongo.errors import DuplicateKeyError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .mongo import get_collection
from .serializers import ConversationSerializer, MessageSerializer


def conversation_group(conversation_id):
    return f"conversation_{conversation_id}"


def users_are_connected(user_id, other_user_id):
    return get_collection("connections").find_one(
        {
            "status": "Accepted",
            "$or": [
                {"requester_id": user_id, "recipient_id": other_user_id},
                {"requester_id": other_user_id, "recipient_id": user_id},
            ],
        },
        {"_id": 1},
    ) is not None


def persist_message(conversation_id, sender_id, content):
    now = datetime.now(timezone.utc)
    message = {
        "conversation_id": ObjectId(conversation_id),
        "sender_id": ObjectId(sender_id),
        "content": content,
        "created_at": now,
        "read_by": [ObjectId(sender_id)],
    }
    inserted_id = get_collection("messages").insert_one(message).inserted_id
    get_collection("conversations").update_one(
        {"_id": ObjectId(conversation_id)},
        {"$set": {"last_message": content, "updated_at": now}},
    )
    payload = {
        "id": str(inserted_id),
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "content": content,
        "created_at": now.isoformat(),
    }
    from channels.layers import get_channel_layer

    layer = get_channel_layer()
    if layer is not None:
        async_to_sync(layer.group_send)(
            conversation_group(conversation_id),
            {"type": "chat.message", "message": payload},
        )
    return payload


class ConversationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = ObjectId(request.user.id)
        conversations = list(
            get_collection("conversations")
            .find({"participants": user_id})
            .sort("updated_at", -1)
            .limit(100)
        )
        conversations = [
            conversation
            for conversation in conversations
            if any(
                participant != user_id and users_are_connected(user_id, participant)
                for participant in conversation["participants"]
            )
        ]
        other_ids = {
            participant
            for conversation in conversations
            for participant in conversation["participants"]
            if participant != user_id
        }
        names = {
            user["_id"]: user["name"]
            for user in get_collection("users").find(
                {"_id": {"$in": list(other_ids)}}, {"name": 1}
            )
        }
        return Response([
            {
                "id": str(conversation["_id"]),
                "participant_id": str(next(
                    participant for participant in conversation["participants"]
                    if participant != user_id
                )),
                "participant_name": names.get(next(
                    participant for participant in conversation["participants"]
                    if participant != user_id
                ), "Student"),
                "last_message": conversation.get("last_message", ""),
                "updated_at": conversation["updated_at"],
            }
            for conversation in conversations
        ])

    def post(self, request):
        serializer = ConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            recipient_id = ObjectId(serializer.validated_data["recipient_id"])
        except Exception:
            return Response({"recipient_id": ["Choose a valid student."]}, status=status.HTTP_400_BAD_REQUEST)
        user_id = ObjectId(request.user.id)
        if recipient_id == user_id:
            return Response({"detail": "You cannot start a conversation with yourself."}, status=status.HTTP_400_BAD_REQUEST)
        recipient = get_collection("users").find_one(
            {"_id": recipient_id, "is_active": True}, {"_id": 1}
        )
        if recipient is None:
            return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)
        if not users_are_connected(user_id, recipient_id):
            return Response(
                {"detail": "You can message a student after they accept your connection request."},
                status=status.HTTP_403_FORBIDDEN,
            )
        participants = sorted([user_id, recipient_id], key=str)
        conversations = get_collection("conversations")
        conversations.create_index("participants", unique=True)
        existing = conversations.find_one({"participants": participants})
        if existing:
            return Response({"id": str(existing["_id"]), "created": False})
        now = datetime.now(timezone.utc)
        try:
            inserted_id = conversations.insert_one({
                "participants": participants,
                "last_message": "",
                "created_at": now,
                "updated_at": now,
            }).inserted_id
        except DuplicateKeyError:
            existing = conversations.find_one({"participants": participants})
            return Response({"id": str(existing["_id"]), "created": False})
        return Response({"id": str(inserted_id), "created": True}, status=status.HTTP_201_CREATED)


class ConversationMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get_conversation(self, request, conversation_id):
        try:
            object_id = ObjectId(conversation_id)
        except Exception:
            return None
        conversation = get_collection("conversations").find_one({
            "_id": object_id,
            "participants": ObjectId(request.user.id),
        })
        if conversation is None:
            return None
        user_id = ObjectId(request.user.id)
        other_user_id = next(
            (participant for participant in conversation["participants"] if participant != user_id),
            None,
        )
        return conversation if other_user_id and users_are_connected(user_id, other_user_id) else None

    def get(self, request, conversation_id):
        conversation = self.get_conversation(request, conversation_id)
        if conversation is None:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        messages = list(
            get_collection("messages")
            .find({"conversation_id": conversation["_id"]})
            .sort("created_at", -1)
            .limit(100)
        )
        messages.reverse()
        current_user_id = ObjectId(request.user.id)
        return Response([
            {
                "id": str(message["_id"]),
                "sender_id": str(message["sender_id"]),
                "content": message["content"],
                "created_at": message["created_at"],
                "is_read": current_user_id in message.get("read_by", []),
            }
            for message in messages
        ])

    def post(self, request, conversation_id):
        if self.get_conversation(request, conversation_id) is None:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = persist_message(conversation_id, request.user.id, serializer.validated_data["content"])
        return Response(message, status=status.HTTP_201_CREATED)

    def patch(self, request, conversation_id):
        conversation = self.get_conversation(request, conversation_id)
        if conversation is None:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        result = get_collection("messages").update_many(
            {"conversation_id": conversation["_id"], "sender_id": {"$ne": ObjectId(request.user.id)}},
            {"$addToSet": {"read_by": ObjectId(request.user.id)}},
        )
        return Response({"marked_read": result.modified_count})


class WebSocketTicketView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        try:
            object_id = ObjectId(conversation_id)
        except Exception:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        user_id = ObjectId(request.user.id)
        if get_collection("conversations").find_one(
            {"_id": object_id, "participants": user_id}, {"_id": 1}
        ) is None:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        ticket = secrets.token_urlsafe(32)
        ticket_hash = hashlib.sha256(ticket.encode()).hexdigest()
        tickets = get_collection("websocket_tickets")
        tickets.create_index("expires_at", expireAfterSeconds=0)
        tickets.insert_one({
            "ticket_hash": ticket_hash,
            "user_id": user_id,
            "conversation_id": object_id,
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=60),
        })
        return Response({"ticket": ticket, "expires_in": 60})


class ConversationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        query = self.scope.get("query_string", b"").decode("ascii", errors="ignore")
        ticket = next(
            (item.split("=", 1)[1] for item in query.split("&") if item.startswith("ticket=")),
            "",
        )
        if not ticket:
            await self.close(code=4401)
            return
        try:
            conversation_object_id = ObjectId(self.conversation_id)
        except Exception:
            await self.close(code=4404)
            return
        ticket_hash = hashlib.sha256(ticket.encode()).hexdigest()
        user_id = await sync_to_async(self.consume_ticket, thread_sensitive=False)(
            ticket_hash, conversation_object_id
        )
        if user_id is None:
            await self.close(code=4401)
            return
        self.user_id = str(user_id)
        self.group_name = conversation_group(self.conversation_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    @staticmethod
    def consume_ticket(ticket_hash, conversation_id):
        now = datetime.now(timezone.utc)
        ticket = get_collection("websocket_tickets").find_one_and_delete({
            "ticket_hash": ticket_hash,
            "conversation_id": conversation_id,
            "expires_at": {"$gt": now},
        })
        if ticket is None:
            return None
        participant = get_collection("conversations").find_one({
            "_id": conversation_id,
            "participants": ticket["user_id"],
        }, {"_id": 1})
        return ticket["user_id"] if participant else None

    async def disconnect(self, close_code):
        group_name = getattr(self, "group_name", None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        serializer = MessageSerializer(data=content)
        if not serializer.is_valid():
            await self.send_json({"type": "error", "errors": serializer.errors})
            return
        message = await sync_to_async(persist_message, thread_sensitive=False)(
            self.conversation_id, self.user_id, serializer.validated_data["content"]
        )
        await self.send_json({"type": "sent", "message_id": message["id"]})

    async def chat_message(self, event):
        await self.send_json({"type": "message", "message": event["message"]})
