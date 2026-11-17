import { useState } from 'react';
import { api, getErrorMessage } from '../api';
import { useAuth } from '../context/AuthContext';
import { PageTitle, ErrorBox } from '../components/UI';
import { DOMAINS, EXPERIENCE, SelectField, splitTags } from '../components/ProfileFields';

export default function ProfilePage() {
  const { user, profile, setProfile, setUser, notify } = useAuth();
  const [form, setForm] = useState({ name: user.name, branch: 'CSE', academic_year: 3, domain: 'AI / ML', experience: 'Beginner', preferred_project_type: 'Web Application', projects_completed: 0, availability_hours: 8, bio: '', city: '', phone: '', github: '', share_contact: false, ...profile, skills: profile?.skills?.join(', ') || '', interests: profile?.interests?.join(', ') || '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [suggestions, setSuggestions] = useState(null);
  const change = e => setForm({ ...form, [e.target.name]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });
  async function save(e) {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const { data } = await api.put('/profiles/me/', { ...form, skills: splitTags(form.skills), interests: splitTags(form.interests) });
      setProfile(data); setUser({ ...user, name: data.name }); notify('Profile saved. Your matches will use these details.');
    } catch (e) { setError(getErrorMessage(e)); } finally { setBusy(false); }
  }
  async function readResume(e) {
    const file = e.target.files[0]; if (!file) return;
    setBusy(true); setError('');
    try { const body = new FormData(); body.append('resume', file); setSuggestions((await api.post('/profiles/resume-suggestions/', body)).data.suggestions); }
    catch (e) { setError(getErrorMessage(e)); } finally { setBusy(false); e.target.value = ''; }
  }
  function applySuggestions() {
    const values = { ...form };
    for (const key of ['skills', 'interests']) if (suggestions[key]?.length) values[key] = [...new Set([...splitTags(form[key]), ...suggestions[key]])].join(', ');
    for (const key of ['name', 'branch', 'domain', 'phone', 'github', 'city']) if (suggestions[key]) values[key] = suggestions[key];
    setForm(values); setSuggestions(null); notify('Suggestions added to the form. Review them before saving.');
  }
  return <><PageTitle eyebrow="YOUR PROFILE" title={profile ? 'Tell your story.' : 'Start with what you love.'}>Your skills and interests help us find people and projects for you.</PageTitle>
    <div className="two-column"><form className="card form-grid" onSubmit={save}>
      <h2 className="full">About you</h2><label>Full name<input name="name" required maxLength={80} value={form.name} onChange={change}/></label>
      <label>Branch<input name="branch" required maxLength={100} value={form.branch} onChange={change}/></label>
      <label>Academic year<input name="academic_year" type="number" min="1" max="4" required value={form.academic_year} onChange={change}/></label>
      <label>City<input name="city" maxLength={100} value={form.city} onChange={change}/></label>
      <label className="full">Bio<textarea name="bio" maxLength={1000} value={form.bio} onChange={change} placeholder="What would you like to build?"/></label>
      <h2 className="full">Skills & interests</h2>
      <label className="full">Skills, separated by commas<input name="skills" required value={form.skills} onChange={change} placeholder="Python, React, machine learning"/><small>Use specific technologies. Similar spellings are normalized when you save.</small></label>
      <label className="full">Interests, separated by commas<input name="interests" required value={form.interests} onChange={change} placeholder="Research, sustainability, education"/></label>
      <SelectField label="Technical domain" name="domain" value={form.domain} onChange={change} options={DOMAINS}/>
      <SelectField label="Experience" name="experience" value={form.experience} onChange={change} options={EXPERIENCE}/>
      <label>Preferred project type<input name="preferred_project_type" required maxLength={80} value={form.preferred_project_type} onChange={change} list="project-types"/></label>
      <label>Hours available each week<input name="availability_hours" type="number" min="1" max="40" required value={form.availability_hours} onChange={change}/></label>
      <label>Projects completed<input name="projects_completed" type="number" min="0" max="100" required value={form.projects_completed} onChange={change}/></label>
      <label>GitHub or portfolio URL<input name="github" type="url" value={form.github} onChange={change}/></label>
      <label>Contact number (optional)<input name="phone" maxLength={40} value={form.phone} onChange={change}/></label>
      <label className="checkbox"><input name="share_contact" type="checkbox" checked={form.share_contact} onChange={change}/>Share my number with accepted connections</label>
      <div className="full"><ErrorBox message={error}/><button className="primary" disabled={busy}>{busy ? 'Saving…' : 'Save profile'}</button></div>
    </form><aside><section className="card"><span className="badge">A LITTLE HEAD START</span><h2>Already have a résumé?</h2><p>Upload a PDF or DOCX to suggest skills. Nothing changes until you review and save.</p><label className="file-picker">Choose résumé<input type="file" accept=".pdf,.docx" disabled={busy} onChange={readResume}/></label><small>Up to 5 MB. Scanned image-only PDFs may have no readable text.</small>{suggestions && <div className="notice"><pre className="suggestions">{JSON.stringify(suggestions, null, 2)}</pre><button type="button" onClick={applySuggestions}>Use these suggestions</button></div>}</section>
      <section className="card tip"><h3>Be specific. Be yourself.</h3><p>Matching uses the details you add here. A fuller profile gives the model better information, but a match score is not a guarantee of a great collaboration.</p></section></aside></div></>;
}
