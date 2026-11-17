import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, getErrorMessage } from '../api';
import { useAuth } from '../context/AuthContext';
import { useData } from '../hooks/useData';
import { DOMAINS, EXPERIENCE, SelectField, splitTags } from '../components/ProfileFields';
import { PageTitle, DataState, Pagination, ProjectCard, ErrorBox } from '../components/UI';

export default function ProjectsPage() {
  const [query, setQuery] = useState(''),
    [search, setSearch] = useState(''),
    [page, setPage] = useState(1);
  const state = useData('/projects/?q=' + encodeURIComponent(search) + '&page=' + page);
  return (
    <>
      <PageTitle
        eyebrow="BUILD SOMETHING TOGETHER"
        title="Big ideas need good teams."
        action={
          <Link className="button primary" to="/projects/new">
            + Create a project
          </Link>
        }
      >
        Explore open projects looking for a fresh perspective.
      </PageTitle>
      <form
        className="search-bar"
        onSubmit={(e) => {
          e.preventDefault();
          setSearch(query);
          setPage(1);
        }}
      >
        <input
          aria-label="Search projects"
          placeholder="Search projects, skills or domains…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button className="primary">Search</button>
      </form>
      <DataState state={state} empty="No open projects found. Yours could be the first.">
        <div className="card-grid">
          {state.data?.items.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
        <Pagination data={state.data} page={page} setPage={setPage} />
      </DataState>
    </>
  );
}
const defaults = {
  title: '',
  description: '',
  required_skills: '',
  required_interests: '',
  domain: 'Web Development',
  project_type: 'Web Application',
  team_size: 4,
  required_experience: 'Beginner',
  expected_hours: 6,
  deadline: '',
};
function localDate(value) {
  if (!value) return '';
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
export function ProjectFormPage() {
  const { id } = useParams(),
    state = useData(id ? '/projects/' + id + '/' : null);
  if (id && state.loading) return <div className="empty">Loading project…</div>;
  if (id && state.error) return <ErrorBox message={state.error} retry={state.reload} />;
  return <ProjectForm key={id || 'new'} initial={state.data} id={id} />;
}
function ProjectForm({ initial, id }) {
  const { notify, user } = useAuth(),
    navigate = useNavigate();
  const [form, setForm] = useState(
    initial
      ? {
          ...initial,
          required_skills: initial.required_skills.join(', '),
          required_interests: (initial.required_interests || []).join(', '),
          deadline: localDate(initial.deadline),
        }
      : defaults,
  );
  const [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  const change = (e) => setForm({ ...form, [e.target.name]: e.target.value });
  if (initial && initial.owner_id !== user.id)
    return <ErrorBox message="Only the project owner can edit this project." />;
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const payload = {
        ...form,
        required_skills: splitTags(form.required_skills),
        required_interests: splitTags(form.required_interests),
        deadline: form.deadline ? new Date(form.deadline).toISOString() : null,
      };
      delete payload.status;
      const { data } = id
        ? await api.patch('/projects/' + id + '/', payload)
        : await api.post('/projects/', payload);
      notify(id ? 'Project updated.' : 'Your project is ready to find its team.');
      navigate('/projects/' + data.id);
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageTitle
        eyebrow="FROM IDEA TO IMPACT"
        title={id ? 'Refine your project.' : 'What will you build?'}
      >
        Tell future teammates what you have in mind.
      </PageTitle>
      <form className="card form-grid form-width" onSubmit={submit}>
        <label className="full">
          Project title
          <input required name="title" maxLength={100} value={form.title} onChange={change} />
        </label>
        <label className="full">
          Description
          <textarea
            required
            rows="5"
            name="description"
            maxLength={3000}
            value={form.description}
            onChange={change}
            placeholder="The problem, your idea, and what teammates will work on…"
          />
        </label>
        <label className="full">
          Required skills, separated by commas
          <input required name="required_skills" value={form.required_skills} onChange={change} />
        </label>
        <label className="full">
          Related interests, separated by commas
          <input name="required_interests" value={form.required_interests} onChange={change} />
        </label>
        <SelectField
          label="Domain"
          name="domain"
          value={form.domain}
          onChange={change}
          options={DOMAINS}
        />
        <label>
          Project type
          <input
            required
            name="project_type"
            maxLength={80}
            value={form.project_type}
            onChange={change}
            list="project-types"
          />
        </label>
        <SelectField
          label="Experience needed"
          name="required_experience"
          value={form.required_experience}
          onChange={change}
          options={EXPERIENCE}
        />
        <label>
          Hours per week
          <input
            required
            name="expected_hours"
            type="number"
            min="1"
            max="40"
            value={form.expected_hours}
            onChange={change}
          />
        </label>
        <label>
          Team size, including you
          <input
            required
            name="team_size"
            type="number"
            min="2"
            max="10"
            value={form.team_size}
            onChange={change}
          />
        </label>
        <label>
          Target deadline (optional)
          <input name="deadline" type="datetime-local" value={form.deadline} onChange={change} />
        </label>
        <div className="full">
          <ErrorBox message={error} />
          <button className="primary" disabled={busy}>
            {busy ? 'Saving…' : id ? 'Save project' : 'Create project'}
          </button>
          <Link className="button subtle" to={id ? '/projects/' + id : '/projects'}>
            Cancel
          </Link>
        </div>
      </form>
    </>
  );
}
