import { useState } from 'react';
import { FileText, ChevronDown, Upload } from 'lucide-react';
import { api, getErrorMessage } from '../api';
import { useAuth } from '../context/AuthContext';
import { PageTitle, ErrorBox } from '../components/UI';
import { DOMAINS, EXPERIENCE, SelectField, splitTags } from '../components/ProfileFields';

export default function ProfilePage() {
  const { user, profile, setProfile, setUser, notify } = useAuth();
  const [form, setForm] = useState({
    name: user.name,
    branch: 'CSE',
    academic_year: 3,
    domain: 'AI / ML',
    experience: 'Beginner',
    preferred_project_type: 'Web Application',
    projects_completed: 0,
    availability_hours: 8,
    bio: '',
    city: '',
    phone: '',
    github: '',
    share_contact: false,
    ...profile,
    skills: profile?.skills?.join(', ') || '',
    interests: profile?.interests?.join(', ') || '',
  });
  const [error, setError] = useState('');
  const [resumeError, setResumeError] = useState('');
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [suggestions, setSuggestions] = useState(null);
  const change = (e) =>
    setForm({
      ...form,
      [e.target.name]: e.target.type === 'checkbox' ? e.target.checked : e.target.value,
    });
  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const { data } = await api.put('/profiles/me/', {
        ...form,
        skills: splitTags(form.skills),
        interests: splitTags(form.interests),
      });
      setProfile(data);
      setUser({ ...user, name: data.name });
      notify('Profile saved. Your matches will use these details.');
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  async function readResume(e) {
    const input = e.target;
    const file = input.files[0];
    if (!file) return;
    setResumeError('');
    setSuggestions(null);
    if (file.size > 5 * 1024 * 1024) {
      setResumeError('Choose a Resume file smaller than 5 MB.');
      input.value = '';
      return;
    }
    setUploading(true);
    try {
      const body = new FormData();
      body.append('resume', file);
      setSuggestions((await api.post('/profiles/resume-suggestions/', body)).data.suggestions);
    } catch (e) {
      setResumeError(getErrorMessage(e));
    } finally {
      setUploading(false);
      input.value = '';
    }
  }
  function applySuggestions() {
    const values = { ...form };
    for (const key of ['skills', 'interests']) {
      if (suggestions[key]?.length) {
        values[key] = [...new Set([...splitTags(form[key]), ...suggestions[key]])].join(', ');
      }
    }
    for (const key of [
      'name',
      'branch',
      'academic_year',
      'domain',
      'experience',
      'preferred_project_type',
      'phone',
      'github',
      'city',
    ]) {
      if (suggestions[key]) values[key] = suggestions[key];
    }
    setForm(values);
    setSuggestions(null);
    notify('Suggestions added to the form. Review them before saving.');
  }
  return (
    <div className="profile-page">
      <PageTitle title={profile ? 'My profile' : 'Create your profile'}>
        Add your skills and interests to find relevant people and projects.
      </PageTitle>
      <details className="resume-panel">
        <summary>
          <span className="resume-icon">
            <FileText size={20} aria-hidden="true" />
          </span>
          <span>
            <strong>Import from Resume</strong>
            <small>Optional · Fill in details from a PDF or DOCX</small>
          </span>
          <ChevronDown className="disclosure-arrow" size={18} aria-hidden="true" />
        </summary>
        <div className="resume-content">
          <p>Upload your Resume, review the suggestions, then save your profile.</p>
          <label className="file-picker">
            <span>
              <Upload size={16} aria-hidden="true" /> Choose Resume
            </span>
            <input
              aria-label="Choose Resume"
              type="file"
              accept=".pdf,.docx"
              disabled={uploading || busy}
              onChange={readResume}
            />
          </label>
          <small className="muted">
            PDF or DOCX, up to 5 MB. Scanned PDFs may not contain readable text.
          </small>
          {uploading && <p role="status">Reading your Resume…</p>}
          <ErrorBox message={resumeError} />
          {suggestions && (
            <div className="resume-results">
              <h3>Review suggestions</h3>
              <dl className="suggestions">
                {Object.entries(suggestions)
                  .filter(([, value]) => value?.length)
                  .map(([key, value]) => (
                    <div key={key}>
                      <dt>{key.replaceAll('_', ' ')}</dt>
                      <dd>{Array.isArray(value) ? value.join(', ') : value}</dd>
                    </div>
                  ))}
              </dl>
              <button type="button" onClick={applySuggestions}>
                Use these suggestions
              </button>
            </div>
          )}
        </div>
      </details>
      <form className="profile-form" onSubmit={save}>
        <section className="profile-section" aria-labelledby="basic-details-title">
          <div className="form-section-heading">
            <h2 id="basic-details-title">Basic details</h2>
            <p>Introduce yourself to your campus.</p>
          </div>
          <div className="form-grid">
            <label>
              Full name
              <input
                name="name"
                required
                maxLength={80}
                value={form.name}
                onChange={change}
                autoComplete="name"
              />
            </label>
            <label>
              Branch
              <input name="branch" required maxLength={100} value={form.branch} onChange={change} />
            </label>
            <label>
              Academic year
              <input
                name="academic_year"
                type="number"
                min="1"
                max="4"
                required
                value={form.academic_year}
                onChange={change}
              />
            </label>
            <label>
              City
              <input
                name="city"
                maxLength={100}
                value={form.city}
                onChange={change}
                autoComplete="address-level2"
              />
            </label>
            <label className="full">
              Bio
              <textarea
                name="bio"
                maxLength={1000}
                value={form.bio}
                onChange={change}
                placeholder="What would you like to build?"
              />
            </label>
          </div>
        </section>
        <section className="profile-section" aria-labelledby="skills-title">
          <div className="form-section-heading">
            <h2 id="skills-title">Skills & interests</h2>
            <p>These details help personalize your recommendations.</p>
          </div>
          <div className="form-grid">
            <label className="full">
              Skills, separated by commas
              <input
                name="skills"
                required
                value={form.skills}
                onChange={change}
                placeholder="Python, React, machine learning"
              />
              <small>Add the technologies you know or are learning.</small>
            </label>
            <label className="full">
              Interests, separated by commas
              <input
                name="interests"
                required
                value={form.interests}
                onChange={change}
                placeholder="Research, sustainability, education"
              />
            </label>
            <SelectField
              label="Technical domain"
              name="domain"
              value={form.domain}
              onChange={change}
              options={DOMAINS}
            />
            <SelectField
              label="Experience"
              name="experience"
              value={form.experience}
              onChange={change}
              options={EXPERIENCE}
            />
          </div>
        </section>
        <section className="profile-section" aria-labelledby="preferences-title">
          <div className="form-section-heading">
            <h2 id="preferences-title">Project preferences</h2>
            <p>Tell potential teammates how you like to work.</p>
          </div>
          <div className="form-grid">
            <label>
              Preferred project type
              <input
                name="preferred_project_type"
                required
                maxLength={80}
                value={form.preferred_project_type}
                onChange={change}
                list="project-types"
              />
            </label>
            <label>
              Hours available each week
              <input
                name="availability_hours"
                type="number"
                min="1"
                max="40"
                required
                value={form.availability_hours}
                onChange={change}
              />
            </label>
            <label>
              Projects completed
              <input
                name="projects_completed"
                type="number"
                min="0"
                max="100"
                required
                value={form.projects_completed}
                onChange={change}
              />
            </label>
          </div>
        </section>
        <section className="profile-section" aria-labelledby="contact-title">
          <div className="form-section-heading">
            <h2 id="contact-title">Links & contact</h2>
            <p>Optional. Choose what you share.</p>
          </div>
          <div className="form-grid">
            <label>
              GitHub or portfolio URL
              <input
                name="github"
                type="url"
                value={form.github}
                onChange={change}
                placeholder="https://github.com/yourname"
              />
            </label>
            <label>
              Contact number (optional)
              <input
                name="phone"
                type="tel"
                maxLength={40}
                value={form.phone}
                onChange={change}
                autoComplete="tel"
              />
            </label>
            <label className="checkbox full">
              <input
                name="share_contact"
                type="checkbox"
                checked={form.share_contact}
                onChange={change}
              />
              Share my number with accepted connections
            </label>
          </div>
        </section>
        <div className="profile-save">
          <ErrorBox message={error} />
          <div className="save-row">
            <span>Your changes are saved only when you click Save.</span>
            <button className="primary" disabled={busy || uploading}>
              {busy ? 'Saving…' : 'Save profile'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
