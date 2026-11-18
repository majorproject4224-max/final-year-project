import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Users, BriefcaseBusiness } from 'lucide-react';
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
  return (
    <>
      <PageTitle
        title={`Welcome, ${user.name.split(' ')[0]}`}
        action={
          <Link className="button primary" to="/projects/new">
            <Plus size={17} />
            Create a project
          </Link>
        }
      >
        Find your next teammate or a project to build together.
      </PageTitle>
      {!profile && (
        <div className="notice">
          Add your skills and interests to get personalized recommendations.{' '}
          <Link to="/profile">Complete profile →</Link>
        </div>
      )}
      <section className="recommendations-section">
        <div className="section-title">
          <h2>Recommended for you</h2>
          <Link to={view === 'students' ? '/students' : '/projects'}>View all {view} →</Link>
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
            Students
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
        <p className="model-note">{state.data?.model_notice}</p>
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
                {expanded ? 'Show fewer' : `Show more ${view}`}
              </button>
            )}
          </DataState>
        ) : (
          <p className="empty">Your recommendations will appear after you complete your profile.</p>
        )}
      </section>
      <section className="activities-section" aria-labelledby="activities-title">
        <div className="section-title"><h2 id="activities-title">Activities for you</h2><Link to="/events">Browse all activities →</Link></div>
        <p className="muted">Discover drives, workshops and meetups that share your interests.</p>
        <DataState state={activities}><div className="card-grid">{activities.data?.items.map((activity) => <ActivityCard key={activity.id} activity={activity} onChanged={activities.reload} />)}</div></DataState>
        <p className="muted activity-preference-link">Suggestions use shared interests and your location preference. <Link to="/profile">Update interests →</Link></p>
      </section>
    </>
  );
}
