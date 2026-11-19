import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, getErrorMessage } from '../api';
import { useAuth } from '../context/AuthContext';
import { useData } from '../hooks/useData';
import { PageTitle, ErrorBox } from '../components/UI';
import { splitTags } from '../components/ProfileFields';
import ResumeTechnologyImport from '../components/ResumeTechnologyImport';

const FIELDS = [
  ['languages', 'Languages you have used', 'LanguageHaveWorkedWith'],
  ['databases', 'Databases you have used', 'DatabaseHaveWorkedWith'],
  ['frameworks', 'Web frameworks you have used', 'WebframeHaveWorkedWith'],
  ['platforms', 'Cloud platforms you have used', 'PlatformHaveWorkedWith'],
  ['wanted_languages', 'Languages you want to use', 'LanguageWantToWorkWith'],
];

export default function ProfilePage() {
  const { user, profile, setProfile, setUser, notify } = useAuth();
  const options = useData('/profiles/options/');
  const [form, setForm] = useState({
    name: user.name, years_code: profile?.years_code ?? '',
    ...Object.fromEntries(FIELDS.map(([key]) => [key, profile?.[key]?.join(', ') || ''])),
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const change = (e) => setForm({ ...form, [e.target.name]: e.target.value });
  async function save(e) {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const { data } = await api.put('/profiles/me/', {
        ...form,
        years_code: form.years_code === '' ? null : Number(form.years_code),
        ...Object.fromEntries(FIELDS.map(([key]) => [key, splitTags(form[key])])),
      });
      setProfile(data); setUser({ ...user, name: data.name });
      notify('Profile saved. Empty fields stay unknown.');
    } catch (e) { setError(getErrorMessage(e)); }
    finally { setBusy(false); }
  }
  const answered = FIELDS.slice(0, 4).filter(([key]) => splitTags(form[key]).length).length + (form.years_code !== '' ? 1 : 0);
  return <div className="profile-page">
    <PageTitle title={profile ? 'My profile' : 'Create your profile'}>Share what you have used and what you want to explore next.</PageTitle>
    <div className="notice survey-source">
      <strong>Built around real developer survey questions</strong>
      <p>Technology fields follow the Stack Overflow Developer Survey 2024. Use your own answers; we never copy a survey respondent into your account.</p>
      <Link to="/method">See how recommendations work →</Link>
    </div>
    <ResumeTechnologyImport options={options.data} onApply={(suggestions) => setForm(previous => ({ ...previous, ...Object.fromEntries(Object.entries(suggestions).map(([key, values]) => [key, [...new Set([...splitTags(previous[key]), ...values])].join(', ')])) }))} />
    <form className="profile-form" onSubmit={save}>
      <section className="profile-section">
        <div className="form-section-heading"><h2>Your name</h2><p>Used for your account, never as a model input.</p></div>
        <label>Full name<input name="name" required maxLength={80} value={form.name} onChange={change} autoComplete="name" /></label>
      </section>
      <section className="profile-section">
        <div className="form-section-heading"><h2>Your technology profile</h2><p>Think about technologies you used during the past year. Leave unanswered fields blank.</p></div>
        <div className="profile-completeness" role="status"><strong>{answered} of 5 input fields answered</strong><span>Completeness describes your answers, not model confidence.</span></div>
        <div className="form-grid">
          {FIELDS.map(([key, title, source]) => <label key={key} className={key === 'wanted_languages' ? 'full' : ''}>
            {title}
            <input name={key} value={form[key]} onChange={change} maxLength={2000} placeholder="Separate technologies with commas" list={'survey-' + key} />
            <datalist id={'survey-' + key}>{options.data?.[key]?.map(value => <option key={value} value={value} />)}</datalist>
            <small className="muted">Survey field: {source}</small>
            {key === 'wanted_languages' && <small className="muted">For the coming year, including technologies you want to keep using. Your answer takes priority over a prediction.</small>}
          </label>)}
          <label>Coding years (including education)
            <input name="years_code" type="number" min="0" max="51" step="0.5" value={form.years_code} onChange={change} placeholder="Optional" />
            <small className="muted">YearsCode · Use 0.5 for less than 1 year, 51 for more than 50.</small>
          </label>
        </div>
        <p className="muted">No technologies entered? You can save and browse manually. The system will ask for more information before making ML suggestions.</p>
      </section>
      <ErrorBox message={error} />
      <button className="primary" disabled={busy}>{busy ? 'Saving…' : 'Save profile'}</button>
    </form>
    <p className="muted">Contact details and interests for drives or meetups are in <Link to="/settings">Community settings</Link>. They are separate from the survey model.</p>
  </div>;
}
