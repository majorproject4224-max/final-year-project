import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import { useData } from '../hooks/useData';
import { PageTitle, DataState, Pagination, ErrorBox, ActionButton, Tags } from '../components/UI';
import {
  ACTIVITY_CATEGORIES,
  ActivityCard,
  ActivityForm,
  ActivityAttendance,
} from '../components/Activities';

export default function EventsPage() {
  const [page, setPage] = useState(1),
    [category, setCategory] = useState(''),
    [scope, setScope] = useState('all');
  const [query, setQuery] = useState(''),
    [search, setSearch] = useState(''),
    [showForm, setShowForm] = useState(false);
  const state = useData(
    `/events/?page=${page}&category=${encodeURIComponent(category)}&scope=${scope}&q=${encodeURIComponent(search)}`,
  );
  const navigate = useNavigate();
  return (
    <>
      <PageTitle
        title="Events & activities"
        action={
          <button className="primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? 'Close form' : '+ Create an activity'}
          </button>
        }
      >
        Volunteer, learn or meet people. Organize as yourself, a club or an organization.
      </PageTitle>
      {showForm && (
        <ActivityForm
          onCancel={() => setShowForm(false)}
          onSaved={(activity) => navigate(`/events/${activity.id}`)}
        />
      )}
      <div className="activity-filters">
        <form
          className="search-bar"
          onSubmit={(e) => {
            e.preventDefault();
            setSearch(query);
            setPage(1);
          }}
        >
          <input
            aria-label="Search activities"
            placeholder="Search activities, interests or cities…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button>Search</button>
        </form>
        <label>
          Category
          <select
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All categories</option>
            {ACTIVITY_CATEGORIES.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          Show
          <select
            value={scope}
            onChange={(e) => {
              setScope(e.target.value);
              setPage(1);
            }}
          >
            <option value="all">All upcoming</option>
            <option value="joined">I'm attending</option>
            <option value="organizing">I'm organizing</option>
          </select>
        </label>
      </div>
      <DataState state={state} empty="No activities here yet. Create one or try another filter.">
        <div className="card-grid">
          {state.data?.items.map((activity) => (
            <ActivityCard key={activity.id} activity={activity} onChanged={state.reload} />
          ))}
        </div>
        <Pagination data={state.data} page={page} setPage={setPage} />
      </DataState>
    </>
  );
}

export function ActivityDetailPage() {
  const { id } = useParams(),
    { user } = useAuth(),
    navigate = useNavigate();
  const state = useData(`/events/${id}/`),
    activity = state.data;
  const owner = activity?.organizer_id === user.id;
  const [editing, setEditing] = useState(false),
    [page, setPage] = useState(1);
  const participants = useData(owner ? `/events/${id}/participants/?page=${page}` : null);
  async function reload() {
    await Promise.all([state.reload(), participants.reload()]);
  }
  if (state.loading) return <div className="empty">Loading activity…</div>;
  if (state.error) return <ErrorBox message={state.error} retry={state.reload} />;
  if (!activity) return null;
  return (
    <>
      <Link className="back-link" to="/events">
        ← All events & activities
      </Link>
      <PageTitle title={activity.title} eyebrow={activity.category}>
        Organized by {activity.organizer_name}
        {activity.organization_name && ` · ${activity.organization_name}`}
      </PageTitle>
      {editing ? (
        <ActivityForm
          activity={activity}
          onCancel={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            reload();
          }}
        />
      ) : (
        <div className="two-column">
          <section className="card activity-detail">
            <h2>About this activity</h2>
            <p className="preserve-lines">{activity.description}</p>
            <Tags values={activity.interest_tags} />
            <dl className="facts">
              <div>
                <dt>When</dt>
                <dd>{new Date(activity.starts_at).toLocaleString()}</dd>
              </div>
              <div>
                <dt>Format</dt>
                <dd>{activity.mode}</dd>
              </div>
              {activity.city && (
                <div>
                  <dt>City</dt>
                  <dd>{activity.city}</dd>
                </div>
              )}
              <div>
                <dt>Location / meeting</dt>
                <dd className="preserve-lines">{activity.location}</dd>
              </div>
              <div>
                <dt>Participants</dt>
                <dd>
                  {activity.attendee_count} attending · {activity.spots_remaining} places left
                </dd>
              </div>
            </dl>
            <div className="activity-buttons">
              <ActivityAttendance activity={activity} onChanged={reload} />
              {owner && (
                <>
                  <button onClick={() => setEditing(true)} disabled={activity.has_started}>
                    Edit activity
                  </button>
                  <ActionButton
                    action={async () => {
                      if (
                        window.confirm(
                          'Delete this activity? Its registrations will also be removed.',
                        )
                      ) {
                        await api.delete(`/events/${id}/`);
                        navigate('/events');
                      }
                    }}
                  >
                    Delete activity
                  </ActionButton>
                </>
              )}
            </div>
          </section>
          <aside className="card">
            {owner ? (
              <>
                <h2>Participants</h2>
                <p className="muted">Only you can see this list.</p>
                <DataState state={participants} empty="No one has joined yet.">
                  <ul className="participant-list">
                    {participants.data?.items.map((person) => (
                      <li key={person.user_id}>{person.name}</li>
                    ))}
                  </ul>
                  <Pagination data={participants.data} page={page} setPage={setPage} />
                </DataState>
              </>
            ) : (
              <>
                <h2>You're welcome here</h2>
                <p>Read the activity details before joining. You can leave if your plans change.</p>
                {activity.is_attending && (
                  <p className="notice">You have a place in this activity.</p>
                )}
              </>
            )}
          </aside>
        </div>
      )}
    </>
  );
}
