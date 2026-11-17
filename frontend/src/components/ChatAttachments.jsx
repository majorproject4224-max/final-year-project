import { useEffect, useRef, useState } from 'react';
import { Download, FileText, LoaderCircle, Paperclip, X } from 'lucide-react';
import { api, getErrorMessage } from '../api';

export const ATTACHMENT_ACCEPT = '.jpg,.jpeg,.png,.webp,.pdf,.docx,.xlsx,.pptx,.txt,.csv,.zip';
export const FILE_LIMIT = 5 * 1024 * 1024;
export const MESSAGE_LIMIT = 10 * 1024 * 1024;

export function fileSize(bytes) {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.ceil(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function DraftAttachments({ files, disabled, onRemove }) {
  if (!files.length) return null;
  return (
    <ul className="draft-attachments" aria-label="Files to send">
      {files.map(({ id, file, preview }) => (
        <li key={id}>
          {preview ? <img src={preview} alt="" /> : <FileText size={24} aria-hidden="true" />}
          <span><strong>{file.name}</strong><small>{fileSize(file.size)}</small></span>
          <button type="button" className="icon-button" disabled={disabled} aria-label={`Remove ${file.name}`} onClick={() => onRemove(id)}>
            <X size={16} aria-hidden="true" />
          </button>
        </li>
      ))}
    </ul>
  );
}

export function AttachButton({ inputRef, disabled, onFiles }) {
  return (
    <>
      <input ref={inputRef} type="file" className="sr-only" tabIndex={-1}
        aria-label="Attach files" multiple accept={ATTACHMENT_ACCEPT} disabled={disabled}
        onChange={(event) => { onFiles(event.target.files); event.target.value = ''; }} />
      <button type="button" className="icon-button attach-button" aria-label="Add files or images"
        title="Add files or images" disabled={disabled} onClick={() => inputRef.current?.click()}>
        <Paperclip size={20} aria-hidden="true" />
      </button>
    </>
  );
}

function ImageViewer({ url, name, onClose }) {
  const dialog = useRef(null);
  useEffect(() => { dialog.current.showModal(); }, []);
  return (
    <dialog ref={dialog} className="image-viewer" onClose={onClose} aria-label={`Image: ${name}`}
      onClick={(event) => { if (event.target === dialog.current) dialog.current.close(); }}>
      <header><span>{name}</span><button className="icon-button" autoFocus aria-label="Close image preview"
        onClick={() => dialog.current.close()}><X size={20} aria-hidden="true" /></button></header>
      <img src={url} alt={name} />
    </dialog>
  );
}

export function MessageAttachment({ conversationId, messageId, attachment }) {
  const element = useRef(null), objectUrl = useRef(null), alive = useRef(true), inFlight = useRef(null);
  const [visible, setVisible] = useState(false), [url, setUrl] = useState(''),
    [busy, setBusy] = useState(false), [error, setError] = useState(''), [open, setOpen] = useState(false);
  const endpoint = `/conversations/${conversationId}/messages/${messageId}/attachments/${attachment.id}/`;
  useEffect(() => {
    alive.current = true;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) { setVisible(true); observer.disconnect(); }
    });
    observer.observe(element.current);
    return () => {
      alive.current = false;
      observer.disconnect();
      if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
    };
  }, []);
  async function load() {
    if (objectUrl.current) return objectUrl.current;
    if (inFlight.current) return inFlight.current;
    setBusy(true);
    setError('');
    // Fetch with the regular JWT client. No credentials or public download URLs go into markup.
    inFlight.current = api.get(endpoint, { responseType: 'blob' }).then(({ data }) => {
      if (!alive.current) return null;
      objectUrl.current = URL.createObjectURL(data);
      setUrl(objectUrl.current);
      return objectUrl.current;
    }).catch(async (failure) => {
      if (failure.response?.data instanceof Blob) {
        try { failure.response.data = JSON.parse(await failure.response.data.text()); } catch { /* Use the generic error below. */ }
      }
      if (alive.current) setError(getErrorMessage(failure));
      return null;
    }).finally(() => {
      inFlight.current = null;
      if (alive.current) setBusy(false);
    });
    return inFlight.current;
  }
  useEffect(() => { if (visible && attachment.is_image) load(); }, [visible]);
  async function download() {
    const address = await load();
    if (!address || !alive.current) return;
    const anchor = document.createElement('a');
    anchor.href = address;
    anchor.download = attachment.name;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  }
  return (
    <div ref={element} className="message-attachment">
      {attachment.is_image && (
        url ? <button type="button" className="attachment-preview" aria-label={`Open image ${attachment.name}`} onClick={() => setOpen(true)}>
          <img src={url} alt={attachment.name} width={attachment.width} height={attachment.height} />
        </button> : <div className="attachment-placeholder">{busy ? 'Loading image…' : 'Image preview'}</div>
      )}
      <div className="attachment-file">
        <FileText size={20} aria-hidden="true" />
        <span><strong>{attachment.name}</strong><small>{fileSize(attachment.size)}</small></span>
        <button type="button" className="icon-button" disabled={busy} aria-label={`Download ${attachment.name}`} onClick={download}>
          {busy ? <LoaderCircle className="spin" size={18} aria-hidden="true" /> : <Download size={18} aria-hidden="true" />}
        </button>
      </div>
      {error && <p className="attachment-error" role="alert">{error} <button type="button" onClick={load}>Retry</button></p>}
      {open && <ImageViewer url={url} name={attachment.name} onClose={() => setOpen(false)} />}
    </div>
  );
}
