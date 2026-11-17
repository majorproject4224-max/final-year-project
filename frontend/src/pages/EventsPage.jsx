import { useState } from 'react';
import { api, getErrorMessage } from '../api';
import { useAuth } from '../context/AuthContext';
import { useData } from '../hooks/useData';
import { PageTitle, DataState, Pagination, ErrorBox, ActionButton } from '../components/UI';
export default function EventsPage() {
  const { user, notify } = useAuth(), [page, setPage] = useState(1), state = useData('/events/?page=' + page);
  const [showForm, setShowForm] = useState(false), [form, setForm] = useState({ title: '', description: '', location: '', starts_at: '' }), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const change = e => setForm({ ...form, [e.target.name]: e.target.value });
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('');
    try { await api.post('/events/', { ...form, starts_at: new Date(form.starts_at).toISOString() }); setShowForm(false); setForm({ title: '', description: '', location: '', starts_at: '' }); await state.reload(); notify('Event created.'); }
    catch (e) { setError(getErrorMessage(e)); } finally { setBusy(false); }
  }
  return <><PageTitle eyebrow="BEYOND THE CLASSROOM" title="Show up. Meet up. Make things." action={<button className="primary" onClick={() => setShowForm(!showForm)}>{showForm ? 'Close form' : '+ Create an event'}</button>}>Workshops, meetups and opportunities to learn together.</PageTitle>
    {showForm && <form className="card form-grid form-width" onSubmit={submit}><h2 className="full">Bring people together</h2><label className="full">Event title<input required maxLength={120} name="title" value={form.title} onChange={change}/></label><label className="full">Description<textarea required maxLength={2000} name="description" value={form.description} onChange={change}/></label><label>Location or meeting link<input required maxLength={160} name="location" value={form.location} onChange={change}/></label><label>Date and time<input required type="datetime-local" name="starts_at" value={form.starts_at} onChange={change}/></label><div className="full"><ErrorBox message={error}/><button className="primary" disabled={busy}>Create event</button></div></form>}
    <DataState state={state} empty="The campus calendar is open. Create the next gathering."><div className="card-grid">{state.data?.items.map(event => <article className="card event-card" key={event.id}><div className="event-date"><strong>{new Date(event.starts_at).getDate()}</strong><span>{new Date(event.starts_at).toLocaleDateString(undefined, { month: 'short' })}</span></div><h2>{event.title}</h2><p className="preserve-lines">{event.description}</p><p className="muted">{new Date(event.starts_at).toLocaleString()}<br/>{event.location}</p><p>{event.attendee_count} attending</p><div className="card-actions"><ActionButton className={event.is_attending ? '' : 'primary'} action={() => event.is_attending ? api.delete('/events/' + event.id + '/attendance/') : api.post('/events/' + event.id + '/attendance/')} onDone={state.reload}>{event.is_attending ? 'Leave event' : "I'll be there"}</ActionButton>{event.organizer_id === user.id && <ActionButton className="subtle danger" action={async () => { if (window.confirm('Delete this event?')) await api.delete('/events/' + event.id + '/'); }} onDone={state.reload}>Delete</ActionButton>}</div></article>)}</div><Pagination data={state.data} page={page} setPage={setPage}/></DataState></>;
}
