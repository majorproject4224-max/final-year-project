import { useState } from 'react';
import { Link } from 'react-router-dom';
import { CalendarDays, MapPin, Users } from 'lucide-react';
import { api, getErrorMessage } from '../api';
import { useAuth } from '../context/AuthContext';
import { ActionButton, ErrorBox, Tags } from './UI';
import { splitTags } from './ProfileFields';

export const ACTIVITY_CATEGORIES = ['Volunteer drive', 'Workshop', 'Meetup', 'Sports', 'Arts & culture', 'Other'];
const SUGGESTED_INTERESTS = ['Community service', 'Volunteering', 'Environmental conservation', 'Agriculture', 'Gardening', 'Sustainability', 'Food donation', 'Photography', 'Programming', 'Education', 'Sports', 'Art'];

export function InterestSuggestions({ value, onChange }) {
  const selected = splitTags(value).map((tag) => tag.toLowerCase());
  return <div className="interest-suggestions" role="group" aria-label="Suggested interests">
    {SUGGESTED_INTERESTS.map((tag) => <button key={tag} type="button" aria-pressed={selected.includes(tag.toLowerCase())}
      onClick={() => onChange(selected.includes(tag.toLowerCase())
        ? splitTags(value).filter((item) => item.toLowerCase() !== tag.toLowerCase()).join(', ')
        : [...splitTags(value), tag].join(', '))}>{tag}</button>)}
  </div>;
}

function localDate(value) {
  if (!value) return '';
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

export function ActivityForm({ activity, onSaved, onCancel }) {
  const { profile, notify } = useAuth();
  const [form, setForm] = useState({
    title: '', description: '', category: 'Volunteer drive', location: '', city: profile?.city || '',
    mode: 'In person', organization_name: profile?.organization_name || '', participant_limit: 30,
    ...activity, starts_at: localDate(activity?.starts_at), interest_tags: activity?.interest_tags?.join(', ') || '',
  });
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const change = (e) => setForm({ ...form, [e.target.name]: e.target.value });
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const payload = { title: form.title, description: form.description, category: form.category,
        location: form.location, city: form.city, mode: form.mode, organization_name: form.organization_name,
        participant_limit: Number(form.participant_limit), starts_at: new Date(form.starts_at).toISOString(),
        interest_tags: splitTags(form.interest_tags) };
      const { data } = activity ? await api.patch(`/events/${activity.id}/`, payload) : await api.post('/events/', payload);
      notify(activity ? 'Activity updated.' : 'Activity published.');
      onSaved(data);
    } catch (e) { setError(getErrorMessage(e)); } finally { setBusy(false); }
  }
  return <form className="card form-grid activity-form" onSubmit={submit}>
    <div className="full"><h2>{activity ? 'Edit activity' : 'Bring people together'}</h2>
      <p className="muted">Anyone can organize. Share a cause, a skill or a common interest.</p></div>
    <label className="full">Activity title<input name="title" required maxLength={120} value={form.title} onChange={change} placeholder="Sunday tree plantation" /></label>
    <label className="full">Description<textarea name="description" required maxLength={2000} value={form.description} onChange={change} placeholder="What will you do together? Explain who can join and what to bring." /></label>
    <label>Category<select name="category" value={form.category} onChange={change}>{ACTIVITY_CATEGORIES.map((item) => <option key={item}>{item}</option>)}</select></label>
    <label>Organization or club (optional)<input name="organization_name" maxLength={120} value={form.organization_name} onChange={change} placeholder="Leave blank when organizing as an individual" /></label>
    <div className="full">
      <label>Activity interests, separated by commas<input name="interest_tags" required value={form.interest_tags} onChange={change} placeholder="Gardening, environmental conservation" /></label>
      <small className="muted">Choose relevant interests below or add your own. These help people find your activity.</small>
      <InterestSuggestions value={form.interest_tags} onChange={(interest_tags) => setForm({ ...form, interest_tags })} />
    </div>
    <label>Format<select name="mode" value={form.mode} onChange={change}><option>In person</option><option>Online</option></select></label>
    <label>City<input name="city" maxLength={100} required={form.mode === 'In person'} value={form.city} onChange={change} placeholder="Delhi" /></label>
    <label className="full">Location or meeting link<input name="location" required maxLength={160} value={form.location} onChange={change} /></label>
    <label>Date and time<input name="starts_at" type="datetime-local" required value={form.starts_at} onChange={change} /><small>Shown in your local time zone.</small></label>
    <label>Participant limit<input name="participant_limit" type="number" min={1} max={500} required value={form.participant_limit} onChange={change} /><small>1–500 participants. Joining reserves a place.</small></label>
    <div className="full"><ErrorBox message={error} /><div className="activity-buttons"><button className="primary" disabled={busy}>{busy ? 'Saving…' : activity ? 'Save changes' : 'Publish activity'}</button><button type="button" onClick={onCancel} disabled={busy}>Cancel</button></div></div>
  </form>;
}

export function ActivityAttendance({ activity, onChanged }) {
  return <ActionButton className={activity.is_attending ? '' : 'primary'}
    disabled={!activity.is_attending && (activity.has_started || !activity.spots_remaining)}
    action={() => activity.is_attending ? api.delete(`/events/${activity.id}/attendance/`) : api.post(`/events/${activity.id}/attendance/`)}
    onDone={onChanged}>
    {activity.is_attending ? 'Leave activity' : activity.has_started ? 'Activity started' : !activity.spots_remaining ? 'Full' : 'Join activity'}
  </ActionButton>;
}

export function ActivityCard({ activity, onChanged }) {
  return <article className="card event-card activity-card">
    <div className="activity-category">{activity.category}</div>
    <h3><Link className="title-link" to={`/events/${activity.id}`}>{activity.title}</Link></h3>
    <p className="muted">By {activity.organizer_name}{activity.organization_name && ` · ${activity.organization_name}`}</p>
    <p className="activity-description">{activity.description}</p>
    <div className="activity-meta">
      <span><CalendarDays size={16} />{new Date(activity.starts_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</span>
      <span><MapPin size={16} />{activity.mode === 'Online' ? 'Online' : activity.city || activity.location}</span>
      <span><Users size={16} />{activity.attendee_count} attending · {activity.spots_remaining} places left</span>
    </div>
    <Tags values={activity.interest_tags} />
    {activity.reasons?.length > 0 && <div className="activity-reasons">{activity.reasons.map((reason) => <p key={reason}>{reason}</p>)}</div>}
    <div className="card-actions"><Link to={`/events/${activity.id}`}>View details →</Link><ActivityAttendance activity={activity} onChanged={onChanged} /></div>
  </article>;
}
