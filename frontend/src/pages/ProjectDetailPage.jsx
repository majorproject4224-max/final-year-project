import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, getErrorMessage } from '../api';
import { useAuth } from '../context/AuthContext';
import { useData } from '../hooks/useData';
import {
  PageTitle,
  ErrorBox,
  Tags,
  ActionButton,
  DataState,
  StudentCard,
  Pagination,
} from '../components/UI';

export default function ProjectDetailPage() {
  const { id } = useParams(),
    { user } = useAuth(),
    state = useData('/projects/' + id + '/');
  if (state.loading) return <div className="empty">Loading project…</div>;
  if (state.error) return <ErrorBox message={state.error} retry={state.reload} />;
  const project = state.data,
    owner = project.owner_id === user.id,
    ended = ['Completed', 'Cancelled'].includes(project.status);
  return (
    <>
      <Link className="back-link" to="/projects">
        ← Explore projects
      </Link>
      <PageTitle
        eyebrow={project.domain.toUpperCase()}
        title={project.title}
        action={
          owner &&
          !ended && (
            <Link className="button" to={'/projects/' + id + '/edit'}>
              Edit project
            </Link>
          )
        }
      >
        Created by {project.owner_name} · {project.status}
      </PageTitle>
      <div className="two-column">
        <div>
          <section className="card">
            <h2>The idea</h2>
            <p className="preserve-lines">{project.description}</p>
            <h3>Skills we're looking for</h3>
            <Tags values={project.required_skills} />
            {project.required_interests?.length > 0 && (
              <>
                <h3>Related interests</h3>
                <Tags values={project.required_interests} />
              </>
            )}
            <dl className="facts">
              <div>
                <dt>Project type</dt>
                <dd>{project.project_type}</dd>
              </div>
              <div>
                <dt>Experience</dt>
                <dd>{project.required_experience}</dd>
              </div>
              <div>
                <dt>Time commitment</dt>
                <dd>{project.expected_hours} hours / week</dd>
              </div>
              <div>
                <dt>Target date</dt>
                <dd>
                  {project.deadline
                    ? new Date(project.deadline).toLocaleDateString()
                    : 'To be discussed'}
                </dd>
              </div>
            </dl>
            {!project.is_member && (
              <div className="notice">
                <p>
                  {project.application_status
                    ? 'Your application: ' + project.application_status
                    : 'Interested? Apply to introduce yourself to the team.'}
                </p>
                {project.application_status === 'Pending' ? (
                  <ActionButton
                    action={() => api.delete('/projects/' + id + '/applications/')}
                    onDone={state.reload}
                  >
                    Withdraw application
                  </ActionButton>
                ) : (
                  !project.application_status &&
                  project.status === 'Open' &&
                  project.team_member_count < project.team_size && (
                    <ActionButton
                      className="primary"
                      action={() => api.post('/projects/' + id + '/applications/', {})}
                      onDone={state.reload}
                    >
                      Apply to project
                    </ActionButton>
                  )
                )}
              </div>
            )}
            {project.is_member && <p className="badge">You're on this team</p>}
          </section>
          {owner && <Applications projectId={id} onChanged={state.reload} />}
          {project.status === 'Completed' && project.is_member && <Feedback project={project} />}
        </div>
        <aside>
          <section className="card">
            <h2>
              The team{' '}
              <span className="muted">
                {project.team_member_count}/{project.team_size}
              </span>
            </h2>
            {project.members.map((member) => (
              <div className="list-row" key={member.id}>
                <div className="grow">
                  <Link to={'/students/' + member.id}>{member.name}</Link>
                  {member.id === project.owner_id && <small>Project owner</small>}
                </div>
                {!ended && member.id !== project.owner_id && (owner || member.id === user.id) && (
                  <ActionButton
                    className="subtle danger"
                    action={async () => {
                      if (
                        window.confirm(
                          member.id === user.id
                            ? 'Leave this team?'
                            : 'Remove this member from the team?',
                        )
                      )
                        await api.delete('/projects/' + id + '/members/' + member.id + '/');
                    }}
                    onDone={state.reload}
                  >
                    {member.id === user.id ? 'Leave' : 'Remove'}
                  </ActionButton>
                )}
              </div>
            ))}
          </section>
          {owner && !ended && (
            <section className="card">
              <h3>Project progress</h3>
              <p>
                Start work when your team is ready. Completing a project enables teammate feedback.
              </p>
              <div className="button-row">
                {project.status === 'Open' && (
                  <ActionButton
                    className="primary"
                    action={() => api.patch('/projects/' + id + '/', { status: 'In Progress' })}
                    onDone={state.reload}
                  >
                    Start project
                  </ActionButton>
                )}
                {project.status === 'In Progress' && (
                  <>
                    <ActionButton
                      className="primary"
                      action={async () => {
                        if (
                          window.confirm(
                            'Mark this project complete? Its membership and details will be preserved.',
                          )
                        )
                          await api.patch('/projects/' + id + '/', { status: 'Completed' });
                      }}
                      onDone={state.reload}
                    >
                      Mark complete
                    </ActionButton>
                    <ActionButton
                      action={() => api.patch('/projects/' + id + '/', { status: 'Open' })}
                      onDone={state.reload}
                    >
                      Reopen recruitment
                    </ActionButton>
                  </>
                )}
                <ActionButton
                  className="subtle danger"
                  action={async () => {
                    if (window.confirm('Cancel this project? This cannot be undone.'))
                      await api.patch('/projects/' + id + '/', { status: 'Cancelled' });
                  }}
                  onDone={state.reload}
                >
                  Cancel project
                </ActionButton>
              </div>
            </section>
          )}
        </aside>
      </div>
      {owner && project.status === 'Open' && <Teammates projectId={id} />}
    </>
  );
}
function Applications({ projectId, onChanged }) {
  const [page, setPage] = useState(1),
    state = useData('/projects/' + projectId + '/applications/?page=' + page);
  return (
    <section className="card">
      <h2>Applications</h2>
      <DataState state={state} empty="Applications will appear here.">
        {state.data?.items.map((item) => (
          <div className="list-row" key={item.id}>
            <div className="grow">
              <Link to={'/students/' + item.user_id}>{item.name}</Link>
              <small>{item.status}</small>
            </div>
            {item.status === 'Pending' &&
              ['Accepted', 'Rejected'].map((decision) => (
                <ActionButton
                  key={decision}
                  className={decision === 'Accepted' ? 'primary' : ''}
                  action={() =>
                    api.patch('/projects/' + projectId + '/applications/', {
                      application_id: item.id,
                      decision,
                    })
                  }
                  onDone={async () => {
                    await state.reload();
                    await onChanged();
                  }}
                >
                  {decision === 'Accepted' ? 'Accept' : 'Decline'}
                </ActionButton>
              ))}
          </div>
        ))}
        <Pagination data={state.data} page={page} setPage={setPage} />
      </DataState>
    </section>
  );
}
function Teammates({ projectId }) {
  const state = useData('/projects/' + projectId + '/teammates/');
  return (
    <section className="section">
      <div className="section-heading">
        <h2>People for this project</h2>
        <Link to="/students">Browse everyone →</Link>
      </div>
      {state.data?.model_notice && <p className="model-note">{state.data.model_notice}</p>}
      <DataState state={state} empty="No teammate suggestions yet.">
        <div className="card-grid">
          {state.data?.items.map((student) => (
            <StudentCard key={student.user_id} student={student} inviteProject={projectId} />
          ))}
        </div>
      </DataState>
    </section>
  );
}
function Feedback({ project }) {
  const { user, notify } = useAuth();
  const [recipient, setRecipient] = useState(''),
    [rating, setRating] = useState('5'),
    [comment, setComment] = useState(''),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api.post('/feedback/', {
        project_id: project.id,
        to_user_id: recipient,
        rating: Number(rating),
        comment,
      });
      notify('Feedback saved. Thank you for reflecting on your collaboration.');
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="card form-grid" onSubmit={submit}>
      <h2 className="full">Reflect on your collaboration</h2>
      <p className="full muted">
        This records real project feedback for future evaluation. Sending again updates your
        feedback.
      </p>
      <label>
        Teammate
        <select required value={recipient} onChange={(e) => setRecipient(e.target.value)}>
          <option value="">Choose a teammate</option>
          {project.members
            .filter((m) => m.id !== user.id)
            .map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
        </select>
      </label>
      <label>
        Collaboration rating
        <select value={rating} onChange={(e) => setRating(e.target.value)}>
          {[5, 4, 3, 2, 1].map((n) => (
            <option key={n} value={n}>
              {n} / 5
            </option>
          ))}
        </select>
      </label>
      <label className="full">
        What worked, and what could improve?
        <textarea maxLength={1000} value={comment} onChange={(e) => setComment(e.target.value)} />
      </label>
      <div className="full">
        <ErrorBox message={error} />
        <button className="primary" disabled={busy}>
          Save feedback
        </button>
      </div>
    </form>
  );
}
