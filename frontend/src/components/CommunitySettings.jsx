import { useState } from 'react';
import { api, getErrorMessage } from '../api';
import { useAuth } from '../context/AuthContext';
import { ErrorBox } from './UI';
import { splitTags } from './ProfileFields';

export default function CommunitySettings() {
  const { profile, user, setProfile, notify } = useAuth();
  const [form, setForm] = useState({ community_interests: profile?.community_interests?.join(', ') || '', city: profile?.city || '', bio: profile?.bio || '', github: profile?.github || '', phone: profile?.phone || '', share_contact: profile?.share_contact || false, organization_name: profile?.organization_name || '', activity_location_preference: profile?.activity_location_preference || 'any' });
  const [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const change = (e) => setForm({ ...form, [e.target.name]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });
  async function save(e) {
    e.preventDefault(); setBusy(true); setError('');
    try { const { data } = await api.put('/profiles/me/', { ...form, name: user.name, community_interests: splitTags(form.community_interests) }); setProfile(data); notify('Community settings saved.'); }
    catch (e) { setError(getErrorMessage(e)); } finally { setBusy(false); }
  }
  return <form className="card form-grid" onSubmit={save}>
    <h2 className="full">Community settings</h2><p className="full muted">These details support contact and activities. They are not inputs or labels for the survey-trained model.</p>
    <label className="full">Community interests, separated by commas<input name="community_interests" value={form.community_interests} onChange={change} placeholder="Gardening, volunteering, photography" /></label>
    <label>City<input name="city" value={form.city} onChange={change} maxLength={100} /></label>
    <label>Organization or club (optional)<input name="organization_name" value={form.organization_name} onChange={change} maxLength={120} /></label>
    <label>Activity location<select aria-label="Activity location" name="activity_location_preference" value={form.activity_location_preference} onChange={change}><option value="any">Any location</option><option value="local">My city and online</option></select></label>
    <label>Portfolio link<input type="url" name="github" value={form.github} onChange={change} /></label>
    <label>Phone (optional)<input name="phone" value={form.phone} onChange={change} maxLength={40} /></label>
    <label className="checkbox"><input name="share_contact" type="checkbox" checked={form.share_contact} onChange={change} />Share phone with accepted connections</label>
    <label className="full">Bio<textarea name="bio" value={form.bio} onChange={change} maxLength={1000} /></label>
    <div className="full"><ErrorBox message={error} /><button className="primary" disabled={busy}>{busy ? 'Saving…' : 'Save community settings'}</button></div>
  </form>;
}
