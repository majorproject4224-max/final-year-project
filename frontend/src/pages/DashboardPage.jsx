import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useData } from '../hooks/useData';
import { DataState, StudentCard, ProjectCard } from '../components/UI';
export default function DashboardPage() {
  const { user, profile } = useAuth();
  const students = useData(profile ? '/recommendations/users/' : null);
  const projects = useData(profile ? '/recommendations/projects/' : null);
  return <><section className="welcome"><p className="eyebrow">YOUR COLLABORATION DESK</p><h1>Make your next<br /><em>connection count.</em></h1><p>Welcome, {user.name}. Your next project starts here.</p><div className="welcome-actions"><Link className="button cream" to="/students">Find collaborators ↗</Link><Link className="welcome-link" to="/projects/new">Start a project →</Link></div><span className="welcome-letter" aria-hidden="true">c.</span></section>
  {!profile && <div className="notice">Add your skills and interests to get personalized recommendations. <Link to="/profile">Complete profile →</Link></div>}
  <section className="section"><div className="section-title"><div><p className="eyebrow">PEOPLE TO BUILD WITH</p><h2>Recommended students</h2></div><Link to="/students">Explore everyone →</Link></div><p className="model-note">{students.data?.model_notice}</p>{profile ? <DataState state={students}><div className="cards">{students.data?.items.map(student => <StudentCard key={student.user_id} student={student} onChanged={students.reload} />)}</div></DataState> : <p className="empty">Your recommendations will appear after you complete your profile.</p>}</section>
  <section className="section"><div className="section-title"><div><p className="eyebrow">IDEAS WITH ROOM FOR YOU</p><h2>Recommended projects</h2></div><Link to="/projects">Browse projects →</Link></div><p className="model-note">{projects.data?.model_notice}</p>{profile && <DataState state={projects}><div className="cards">{projects.data?.items.map(project => <ProjectCard key={project.id} project={project} onChanged={projects.reload} />)}</div></DataState>}</section></>;
}
