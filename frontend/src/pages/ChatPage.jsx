import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, WS_URL, getErrorMessage } from '../api';
import { useAuth } from '../context/AuthContext';
import { useData } from '../hooks/useData';
import { PageTitle, Avatar, ErrorBox } from '../components/UI';
import { ATTACHMENT_ACCEPT, FILE_LIMIT, MESSAGE_LIMIT, AttachButton, DraftAttachments, MessageAttachment } from '../components/ChatAttachments';

export default function ChatPage() {
  const { id } = useParams(),
    navigate = useNavigate(),
    conversations = useData('/conversations/');
  useEffect(() => {
    const timer = setInterval(conversations.reload, 30000);
    return () => clearInterval(timer);
  }, [conversations.reload]);
  const current = conversations.data?.items.find((item) => item.id === id);
  return (
    <>
      <PageTitle
        title="Messages"
        action={
          <Link className="button" to="/connections">
            Message a connection
          </Link>
        }
      >
        Plan your next step with the people in your circle.
      </PageTitle>
      <div className="chat-layout">
        <aside className="conversation-list">
          <h2>Messages</h2>
          <ErrorBox message={conversations.error} retry={conversations.reload} />
          {conversations.loading && !conversations.data && <p>Loading conversations…</p>}
          {conversations.data?.items.map((item) => (
            <button
              className={'conversation ' + (id === item.id ? 'selected' : '')}
              key={item.id}
              onClick={() => navigate('/chat/' + item.id)}
            >
              <Avatar name={item.participant_name} />
              <span>
                <strong>{item.participant_name}</strong>
                <small>{item.last_message || 'Say hello'}</small>
              </span>
              {item.unread_count > 0 && <span className="unread">{item.unread_count}</span>}
            </button>
          ))}
          {conversations.data?.items.length === 0 && (
            <p className="muted">Start a conversation from an accepted connection's profile.</p>
          )}
        </aside>
        {id ? (
          <Conversation
            key={id}
            id={id}
            name={current?.participant_name || 'Conversation'}
            onUpdate={conversations.reload}
          />
        ) : (
          <div className="chat-empty">
            <span className="chat-illustration" aria-hidden="true">
              “
            </span>
            <h2>Every idea starts somewhere.</h2>
            <p>Choose a conversation, or message one of your connections.</p>
            <Link to="/connections">Find your circle →</Link>
          </div>
        )}
      </div>
    </>
  );
}
function Conversation({ id, name, onUpdate }) {
  const { user } = useAuth(),
    [messages, setMessages] = useState([]),
    [text, setText] = useState(''),
    [error, setError] = useState(''),
    [status, setStatus] = useState('Connecting…'),
    [sending, setSending] = useState(false),
    [files, setFiles] = useState([]),
    [uploadProgress, setUploadProgress] = useState(0),
    [dragging, setDragging] = useState(false),
    [older, setOlder] = useState(false),
    [loadingOlder, setLoadingOlder] = useState(false);
  const known = useRef([]),
    pending = useRef(null),
    draftFiles = useRef([]),
    fileInput = useRef(null),
    viewport = useRef(null),
    markBusy = useRef(false),
    alive = useRef(true);
  const endpoint = '/conversations/' + id + '/messages/';
  function addFiles(selected) {
    if (sending) return;
    const incoming = Array.from(selected || []);
    if (!incoming.length) return;
    const all = [...draftFiles.current.map(({ file }) => file), ...incoming];
    if (all.length > 3) { setError('Attach up to 3 files per message.'); return; }
    if (all.some((file) => !file.size || file.size > FILE_LIMIT) || all.reduce((sum, file) => sum + file.size, 0) > MESSAGE_LIMIT) {
      setError('Files must not be empty, and must be at most 5 MB each / 10 MB total.'); return;
    }
    if (incoming.some((file) => !ATTACHMENT_ACCEPT.split(',').includes('.' + file.name.split('.').pop().toLowerCase()))) {
      setError('Use JPG, PNG, WebP, PDF, DOCX, XLSX, PPTX, TXT, CSV or ZIP files.'); return;
    }
    draftFiles.current = [...draftFiles.current, ...incoming.map((file) => ({
      id: crypto.randomUUID(), file,
      preview: /\.(jpe?g|png|webp)$/i.test(file.name) ? URL.createObjectURL(file) : null,
    }))];
    setFiles(draftFiles.current);
    setError('');
  }
  function removeFile(identifier) {
    const item = draftFiles.current.find(({ id }) => id === identifier);
    if (item?.preview) URL.revokeObjectURL(item.preview);
    draftFiles.current = draftFiles.current.filter(({ id }) => id !== identifier);
    setFiles(draftFiles.current);
  }
  useEffect(() => () => {
    draftFiles.current.forEach(({ preview }) => { if (preview) URL.revokeObjectURL(preview); });
  }, []);
  function merge(rows) {
    const nearBottom =
      !viewport.current ||
      viewport.current.scrollHeight - viewport.current.scrollTop - viewport.current.clientHeight <
        100;
    const merged = new Map(known.current.map((row) => [row.id, row]));
    for (const row of rows) merged.set(row.id, row);
    known.current = [...merged.values()].sort((a, b) => a.id.localeCompare(b.id));
    setMessages(known.current);
    if (nearBottom)
      requestAnimationFrame(() => {
        if (viewport.current) viewport.current.scrollTop = viewport.current.scrollHeight;
      });
  }
  async function markRead() {
    const last = known.current.at(-1);
    if (
      !alive.current ||
      document.visibilityState !== 'visible' ||
      !last ||
      markBusy.current ||
      !known.current.some((m) => m.sender_id !== user.id && !m.read_by.includes(user.id))
    )
      return;
    markBusy.current = true;
    try {
      await api.patch(endpoint, { through: last.id });
      if (alive.current) {
        known.current = known.current.map((m) =>
          m.id <= last.id ? { ...m, read_by: [...new Set([...m.read_by, user.id])] } : m,
        );
        setMessages([...known.current]);
        onUpdate();
      }
    } catch (e) {
      if (alive.current) setError(getErrorMessage(e));
    } finally {
      markBusy.current = false;
    }
  }
  useEffect(() => {
    alive.current = true;
    let stopped = false,
      socket,
      retryTimer,
      attempts = 0;
    async function syncHistory() {
      let cursor = known.current.at(-1)?.id,
        more = true;
      while (!stopped && more) {
        const { data } = await api.get(endpoint + (cursor ? '?after=' + cursor : ''));
        if (stopped) return;
        merge(data.items);
        if (!cursor) {
          setOlder(data.has_more);
          break;
        }
        cursor = data.cursor;
        more = data.has_more && !!cursor;
      }
      if (!stopped) await markRead();
    }
    async function connect() {
      if (stopped) return;
      setStatus(attempts ? 'Reconnecting…' : 'Connecting…');
      try {
        const { data } = await api.post('/conversations/' + id + '/websocket-ticket/');
        if (stopped) return;
        socket = new WebSocket(
          WS_URL + '/ws/conversations/' + id + '/?ticket=' + encodeURIComponent(data.ticket),
        );
        socket.onopen = () => {
          if (stopped) return;
          attempts = 0;
          setStatus('Live');
          setError('');
          syncHistory().catch((e) => {
            if (!stopped) setError(getErrorMessage(e));
          });
        };
        socket.onmessage = (event) => {
          if (stopped) return;
          const data = JSON.parse(event.data);
          if (data.type === 'message') {
            merge([data.message]);
            markRead();
            onUpdate();
          }
          if (data.type === 'read') {
            known.current = known.current.map((m) =>
              m.id <= data.through
                ? { ...m, read_by: [...new Set([...m.read_by, data.reader_id])] }
                : m,
            );
            setMessages([...known.current]);
          }
          if (data.type === 'error') setError(data.detail || 'The message could not be delivered.');
        };
        socket.onclose = () => scheduleRetry();
        socket.onerror = () => socket.close();
      } catch (e) {
        if (stopped) return;
        setError(getErrorMessage(e));
        if ([401, 403, 404].includes(e.response?.status)) {
          setStatus('Unavailable');
          return;
        }
        scheduleRetry();
      }
    }
    function scheduleRetry() {
      if (stopped) return;
      setStatus('Reconnecting…');
      retryTimer = setTimeout(connect, Math.min(30000, 1000 * 2 ** Math.min(attempts++, 5)));
    }
    syncHistory().catch((e) => {
      if (!stopped) setError(getErrorMessage(e));
    });
    connect();
    const visibility = () => {
      if (document.visibilityState === 'visible') markRead();
    };
    document.addEventListener('visibilitychange', visibility);
    return () => {
      stopped = true;
      alive.current = false;
      clearTimeout(retryTimer);
      socket?.close();
      document.removeEventListener('visibilitychange', visibility);
    };
  }, [id]);
  async function send(e) {
    e.preventDefault();
    if ((!text.trim() && !files.length) || sending) return;
    setSending(true);
    setUploadProgress(0);
    setError('');
    // Keep the same identifier on retry, so a lost response cannot duplicate a message.
    const fileKey = files.map(({ id }) => id).join(',');
    if (!pending.current || pending.current.content !== text.trim() || pending.current.fileKey !== fileKey)
      pending.current = { content: text.trim(), client_id: crypto.randomUUID(), fileKey };
    const payload = new FormData();
    payload.append('content', pending.current.content);
    payload.append('client_id', pending.current.client_id);
    files.forEach(({ file }) => payload.append('attachments', file));
    try {
      const { data } = await api.post(endpoint, payload, {
        onUploadProgress: ({ loaded, total }) => { if (alive.current && total) setUploadProgress(Math.round(loaded / total * 100)); },
      });
      if (alive.current) {
        merge([data]);
        setText('');
        draftFiles.current.forEach(({ preview }) => { if (preview) URL.revokeObjectURL(preview); });
        draftFiles.current = [];
        setFiles([]);
        pending.current = null;
        onUpdate();
      }
    } catch (e) {
      if (alive.current) setError(getErrorMessage(e));
    } finally {
      if (alive.current) setSending(false);
    }
  }
  async function loadOlder() {
    setLoadingOlder(true);
    const element = viewport.current,
      height = element?.scrollHeight || 0;
    try {
      const { data } = await api.get(endpoint + '?before=' + known.current[0].id);
      merge(data.items);
      setOlder(data.has_more);
      requestAnimationFrame(() => {
        if (element) element.scrollTop = element.scrollHeight - height;
      });
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setLoadingOlder(false);
    }
  }
  return (
    <section className={'chat-panel' + (dragging ? ' dragging' : '')}
      onDragOver={(event) => { if (event.dataTransfer.types.includes('Files')) { event.preventDefault(); setDragging(true); } }}
      onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setDragging(false); }}
      onDrop={(event) => { event.preventDefault(); setDragging(false); addFiles(event.dataTransfer.files); }}>
      {dragging && <div className="chat-dropzone">Drop files to attach</div>}
      <header>
        <Avatar name={name} />
        <div>
          <h2>{name}</h2>
          <small className={status === 'Live' ? 'live' : ''}>{status}</small>
        </div>
      </header>
      <ErrorBox message={error} />
      <div
        className="message-history"
        ref={viewport}
        role="log"
        aria-label="Conversation messages"
        aria-live="polite"
      >
        {older && (
          <button className="load-older" disabled={loadingOlder} onClick={loadOlder}>
            Load earlier messages
          </button>
        )}
        {messages.length === 0 && (
          <p className="empty">Say hello and share what you're working on.</p>
        )}
        {messages.map((message) => (
          <div
            className={'message ' + (message.sender_id === user.id ? 'mine' : '')}
            key={message.id}
          >
            {message.attachments?.length > 0 && <div className="message-attachments">
              {message.attachments.map((attachment) => <MessageAttachment key={attachment.id} conversationId={id} messageId={message.id} attachment={attachment} />)}
            </div>}
            {message.content && <p>{message.content}</p>}
            <small>
              {new Date(message.created_at).toLocaleString([], {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
              {message.sender_id === user.id &&
                ' · ' + (message.read_by.some((id) => id !== user.id) ? 'Read' : 'Sent')}
            </small>
          </div>
        ))}
      </div>
      <form className="message-compose" onSubmit={send}
        onPaste={(event) => { if (event.clipboardData.files.length) { event.preventDefault(); addFiles(event.clipboardData.files); } }}>
        <DraftAttachments files={files} disabled={sending} onRemove={removeFile} />
        <div className="compose-controls">
        <AttachButton inputRef={fileInput} disabled={sending || status === 'Unavailable'} onFiles={addFiles} />
        <label className="sr-only" htmlFor="message">
          Message
        </label>
        <input
          id="message"
          autoComplete="off"
          maxLength={4000}
          placeholder="Share an idea…"
          value={text}
          disabled={sending || status === 'Unavailable'}
          onChange={(e) => setText(e.target.value)}
        />
        <button className="primary" disabled={sending || (!text.trim() && !files.length) || status === 'Unavailable'}>
          {sending ? (files.length && uploadProgress < 100 ? `${uploadProgress}%` : 'Sending…') : 'Send'}
        </button>
        </div>
        <p className="compose-hint" id="attachment-help">Add images or documents · 3 files, 5 MB each · 10 MB total</p>
        {sending && <span className="sr-only" role="status">Sending message{files.length ? ` with attachments: ${uploadProgress}% uploaded` : ''}</span>}
      </form>
    </section>
  );
}
