import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useData } from '../hooks/useData';
import { PageTitle, DataState, Pagination, ProjectCard, ActionButton } from '../components/UI';
export default function MySpacePage() {
  const [page, setPage] = useState(1),
    [invitePage, setInvitePage] = useState(1);
  const projects = useData('/projects/?mine=1&page=' + page),
    invitations = useData('/invitations/?page=' + invitePage),
    saved = useData('/interactions/');
  return (
    <>
      <PageTitle
        title="My space"
        action={
          <Link className="button primary" to="/projects/new">
            + Create a project
          </Link>
        }
      >
        Your teams, invitations and saved projects.
      </PageTitle>
      <section className="section">
        <h2>Your projects & teams</h2>
        <DataState state={projects} empty="Create or join a project to find your team here.">
          <div className="card-grid">
            {projects.data?.items.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
          <Pagination data={projects.data} page={page} setPage={setPage} />
        </DataState>
      </section>
      <section className="section">
        <h2>Team invitations</h2>
        <DataState state={invitations} empty="No invitations yet.">
          <div className="card">
            {invitations.data?.items.map((item) => (
              <div className="list-row" key={item.id}>
                <div className="grow">
                  <Link className="title-link" to={'/projects/' + item.project_id}>
                    {item.project_title}
                  </Link>
                  <p className="muted">
                    {item.direction === 'sent'
                      ? 'Sent to ' + item.recipient_name
                      : 'Invitation for you'}{' '}
                    · {item.status}
                  </p>
                </div>
                {item.status === 'Pending' &&
                  item.direction === 'received' &&
                  ['Accepted', 'Rejected'].map((decision) => (
                    <ActionButton
                      key={decision}
                      className={decision === 'Accepted' ? 'primary' : ''}
                      action={() => api.patch('/invitations/' + item.id + '/', { decision })}
                      onDone={async () => {
                        await invitations.reload();
                        await projects.reload();
                      }}
                    >
                      {decision === 'Accepted' ? 'Join team' : 'Decline'}
                    </ActionButton>
                  ))}
                {item.status === 'Pending' && item.direction === 'sent' && (
                  <ActionButton
                    action={() => api.delete('/invitations/' + item.id + '/')}
                    onDone={invitations.reload}
                  >
                    Cancel invite
                  </ActionButton>
                )}
              </div>
            ))}
          </div>
          <Pagination data={invitations.data} page={invitePage} setPage={setInvitePage} />
        </DataState>
      </section>
      <section className="section">
        <h2>Saved projects</h2>
        <DataState state={saved} empty="Save a project while exploring to return to it later.">
          <div className="card-grid">
            {saved.data?.items
              .filter((item) => item.target_type === 'project')
              .map((item) => (
                <SavedProject key={item.target_id} id={item.target_id} reload={saved.reload} />
              ))}
          </div>
        </DataState>
      </section>
    </>
  );
}
function SavedProject({ id, reload }) {
  const state = useData('/projects/' + id + '/');
  return (
    <section>
      {state.data ? (
        <ProjectCard project={state.data} />
      ) : (
        <p>{state.loading ? 'Loading saved project…' : state.error || 'Project unavailable'}</p>
      )}
      <ActionButton
        className="subtle"
        action={() =>
          api.post('/interactions/', { target_type: 'project', target_id: id, action: 'unsave' })
        }
        onDone={reload}
      >
        Remove from saved
      </ActionButton>
    </section>
  );
}
