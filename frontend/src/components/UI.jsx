import { Link } from 'react-router-dom';
import { useState } from 'react';
import { api, getErrorMessage } from '../api';
import { useAuth } from '../context/AuthContext';

export function PageTitle({ eyebrow, title, children, action }) {
  return (
    <header className="page-title">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {children && <p className="subtitle">{children}</p>}
      </div>
      {action}
    </header>
  );
}
export function ErrorBox({ message, retry }) {
  return message ? (
    <div className="notice error" role="alert">
      {message}
      {retry && <button onClick={retry}>Try again</button>}
    </div>
  ) : null;
}
export function DataState({ state, children, empty = 'Nothing here yet.' }) {
  if (state.loading)
    return (
      <div className="empty" role="status">
        Loading…
      </div>
    );
  if (state.error) return <ErrorBox message={state.error} retry={state.reload} />;
  if (!state.data?.items?.length) return <div className="empty">{state.data?.detail || empty}</div>;
  return children;
}
export function Pagination({ data, page, setPage }) {
  if (!data || data.total <= data.page_size) return null;
  return (
    <div className="pagination">
      <button disabled={page === 1} onClick={() => setPage(page - 1)}>
        Previous
      </button>
      <span>
        Page {page} · {data.total} results
      </span>
      <button disabled={page * data.page_size >= data.total} onClick={() => setPage(page + 1)}>
        Next
      </button>
    </div>
  );
}
export function Tags({ values = [] }) {
  return (
    <div className="tags">
      {values.map((value) => (
        <span key={value}>{value}</span>
      ))}
    </div>
  );
}
export function Avatar({ name = 'Student', large = false }) {
  return (
    <span className={`avatar ${large ? 'large' : ''}`} aria-hidden="true">
      {name
        .split(' ')
        .slice(0, 2)
        .map((word) => word[0])
        .join('')}
    </span>
  );
}
export function Explanations({ items = [] }) {
  if (!items.length) return null;
  return (
    <details className="match-details">
      <summary>Why this match?</summary>
      <ul className="reasons">
        {items.map((reason, i) => (
          <li key={i}>
            {reason.items
              ? `${{ shared_skills: 'Shared skills', shared_interests: 'Common interests', required_skills_matched: 'Required skills matched', skills_to_learn: 'Skills to learn' }[reason.feature] || reason.feature}: ${reason.items.join(', ')}`
              : reason.feature === 'same_domain'
                ? 'Same domain: ' + reason.value
                : reason.feature === 'same_project_type'
                  ? 'Shared project preference: ' + reason.value
                  : reason.value}
          </li>
        ))}
      </ul>
    </details>
  );
}
export function ActionButton({ action, children, className = '', onDone, ...props }) {
  const [busy, setBusy] = useState(false);
  const { notify } = useAuth();
  async function run() {
    setBusy(true);
    try {
      await action();
      if (onDone) await onDone();
    } catch (e) {
      notify(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <button {...props} className={className} disabled={busy || props.disabled} onClick={run}>
      {busy ? 'Working…' : children}
    </button>
  );
}
export function StudentCard({ student, onChanged, inviteProject }) {
  const { notify } = useAuth();
  const connection = student.connection;
  const pending = connection?.status === 'Pending';
  const accepted = connection?.status === 'Accepted';
  return (
    <article className="card student-card">
      <div className="card-top">
        <Avatar name={student.name} />
        <div>
          <Link className="title-link" to={`/students/${student.user_id}`}>
            {student.name}
          </Link>
          <p className="muted">
            {student.organization_name || student.domain}{student.academic_year ? ` · Year ${student.academic_year}` : ''}
          </p>
        </div>
        {student.compatibility_score != null && (
          <span className="score">
            {student.compatibility_score}% <small>match</small>
          </span>
        )}
      </div>
      <Tags values={student.skills?.slice(0, 6)} />
      <Explanations items={student.explanations} />
      <div className="card-actions">
        <Link to={`/students/${student.user_id}`}>View profile →</Link>
        {inviteProject ? (
          <ActionButton
            className="primary"
            action={() =>
              api.post('/invitations/', {
                project_id: inviteProject,
                recipient_id: student.user_id,
              })
            }
            onDone={() => notify('Invitation sent.')}
          >
            Invite
          </ActionButton>
        ) : (
          <ActionButton
            disabled={accepted || (pending && connection.direction === 'sent')}
            action={() =>
              pending
                ? api.patch(`/connections/${connection.id}/`, { action: 'accept' })
                : api.post('/connections/', { user_id: student.user_id })
            }
            onDone={async () => {
              notify(pending ? 'Connection accepted.' : 'Connection request sent.');
              onChanged?.();
            }}
          >
            {accepted
              ? 'Connected'
              : pending
                ? connection.direction === 'received'
                  ? 'Accept request'
                  : 'Request sent'
                : 'Connect'}
          </ActionButton>
        )}
        {student.compatibility_score != null && (
          <ActionButton
            className="subtle"
            action={() =>
              api.post('/interactions/', {
                target_type: 'student',
                target_id: student.user_id,
                action: 'ignore',
              })
            }
            onDone={onChanged}
          >
            Hide
          </ActionButton>
        )}
      </div>
    </article>
  );
}
export function ProjectCard({ project, onChanged }) {
  const { notify } = useAuth();
  return (
    <article className="card project-card">
      <div className="card-top">
        <span className="badge">{project.domain}</span>
        {project.compatibility_score != null && (
          <span className="score">
            {project.compatibility_score}% <small>match</small>
          </span>
        )}
      </div>
      <Link className="title-link" to={`/projects/${project.id}`}>
        {project.title}
      </Link>
      <p className="description">{project.description}</p>
      <Tags values={project.required_skills} />
      <p className="muted">
        {project.team_member_count}/{project.team_size} members · {project.status}
      </p>
      <Explanations items={project.explanations} />
      <div className="card-actions">
        <Link to={`/projects/${project.id}`}>View project →</Link>
        <ActionButton
          action={() =>
            api.post('/interactions/', {
              target_type: 'project',
              target_id: project.id,
              action: 'save',
            })
          }
          onDone={() => notify('Project saved. Find it in My space.')}
        >
          Save
        </ActionButton>
        {project.compatibility_score != null && (
          <ActionButton
            className="subtle"
            action={() =>
              api.post('/interactions/', {
                target_type: 'project',
                target_id: project.id,
                action: 'ignore',
              })
            }
            onDone={onChanged}
          >
            Hide
          </ActionButton>
        )}
      </div>
    </article>
  );
}
