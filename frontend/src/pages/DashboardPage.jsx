import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Users, BriefcaseBusiness, CalendarDays } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useData } from '../hooks/useData';
import { PageTitle, DataState, StudentCard, ProjectCard } from '../components/UI';
import { ActivityCard } from '../components/Activities';
export default function DashboardPage() {
  const { user, profile } = useAuth();
  const [view, setView] = useState('students');
  const [expanded, setExpanded] = useState(false);
  const students = useData(profile ? '/recommendations/users/' : null);
  const projects = useData(profile ? '/recommendations/projects/' : null);
  const activities = useData('/recommendations/activities/');
  const state = view === 'students' ? students : projects;
  const viewLabel = view === 'students' ? 'people' : 'projects';
  return (
    <>
      <div className="dashboard-welcome">
        <PageTitle
          eyebrow="YOUR COMMUNITY"
          title={`Welcome, ${user.name.split(' ')[0]}`}
          action={
            <div className="welcome-actions">
              <Link className="button primary" to="/projects/new">
                <Plus size={17} />
                Create a project
              </Link>
              <Link className="button" to="/events">
                <CalendarDays size={17} />
                Explore activities
              </Link>
            </div>
          }
        >
          Discover learning partners, build projects and take part in community activities.
        </PageTitle>
      </div>
      {!profile && (
        <div className="notice">
          Add your skills and interests to get personalized recommendations.{' '}
          <Link to="/profile">Complete profile →</Link>
        </div>
      )}
      <section className="recommendations-section">
        <div className="section-title">
          <h2>Recommended for you</h2>
          <Link to={view === 'students' ? '/students' : '/projects'}>View all {viewLabel} →</Link>
        </div>
        <div className="view-switch" role="group" aria-label="Recommendation type">
          <button
            aria-pressed={view === 'students'}
            onClick={() => {
              setView('students');
              setExpanded(false);
            }}
          >
            <Users size={17} />
            People
          </button>
          <button
            aria-pressed={view === 'projects'}
            onClick={() => {
              setView('projects');
              setExpanded(false);
            }}
          >
            <BriefcaseBusiness size={17} />
            Projects
          </button>
        </div>
        <p className="model-note">{state.data?.model_notice} <Link to="/method">How it works →</Link></p>
        {view === 'students' && students.data?.profile_quality && <div className="profile-completeness"><strong>{students.data.profile_quality.observed_input_fields}/5 technology input fields answered</strong><span>Missing answers remain unknown. <Link to="/profile">Review profile →</Link></span></div>}
        {profile ? (
          <DataState state={state}>
            <div className="cards">
              {state.data?.items
                .slice(0, expanded ? 12 : 4)
                .map((item) =>
                  view === 'students' ? (
                    <StudentCard key={item.user_id} student={item} onChanged={students.reload} />
                  ) : (
                    <ProjectCard key={item.id} project={item} onChanged={projects.reload} />
                  ),
                )}
            </div>
            {state.data?.items.length > 4 && (
              <button className="show-more" onClick={() => setExpanded(!expanded)}>
                {expanded ? 'Show fewer' : `Show more ${viewLabel}`}
              </button>
            )}
          </DataState>
        ) : (
          <p className="empty">Your recommendations will appear after you complete your profile.</p>
        )}
      </section>
      <section className="activities-section" aria-labelledby="activities-title">
        <div className="section-title">
          <h2 id="activities-title">Activities for you</h2>
          <Link to="/events">Browse all activities →</Link>
        </div>
        <p className="muted">Discover drives, workshops and meetups that share your interests.</p>
        <DataState state={activities}>
          <div className="card-grid">
            {activities.data?.items.map((activity) => (
              <ActivityCard key={activity.id} activity={activity} onChanged={activities.reload} />
            ))}
          </div>
        </DataState>
        <p className="muted activity-preference-link">
          Suggestions use shared interests and your location preference.{' '}
          <Link to="/settings">Update community interests →</Link>
        </p>
      </section>
    </>
  );
}
