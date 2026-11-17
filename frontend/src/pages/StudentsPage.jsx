import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import { useData } from '../hooks/useData';
import { PageTitle, DataState, Pagination, StudentCard, ErrorBox, Avatar, Tags, ActionButton } from '../components/UI';

export default function StudentsPage() {
  const [query, setQuery] = useState(''), [search, setSearch] = useState(''), [page, setPage] = useState(1);
  const state = useData('/students/?q=' + encodeURIComponent(search) + '&page=' + page);
  return <><PageTitle eyebrow="THE CAMPUS COMMUNITY" title="Your next teammate is here.">Find people who share your curiosity, or bring a different skill to the table.</PageTitle>
    <form className="search-bar" onSubmit={e => { e.preventDefault(); setSearch(query); setPage(1); }}><input aria-label="Search students" placeholder="Search names, skills or interests…" value={query} onChange={e => setQuery(e.target.value)}/><button className="primary">Search</button></form>
    <DataState state={state} empty="No students match your search yet."><div className="card-grid">{state.data?.items.map(student => <StudentCard key={student.user_id} student={student} onChanged={state.reload}/>)}</div><Pagination data={state.data} page={page} setPage={setPage}/></DataState></>;
}
export function StudentDetailPage() {
  const { id } = useParams(), navigate = useNavigate(), { user } = useAuth();
  const state = useData('/students/' + id + '/');
  const student = state.data;
  if (state.loading) return <div className="empty">Loading profile…</div>;
  if (state.error) return <ErrorBox message={state.error} retry={state.reload}/>;
  return <><Link className="back-link" to="/students">← All students</Link><PageTitle eyebrow="STUDENT PROFILE" title={student.name}>{student.branch} · Year {student.academic_year} · {student.city || 'Campus community'}</PageTitle>
    <div className="two-column"><section className="card"><Avatar name={student.name} large/><h2>About {student.name.split(' ')[0]}</h2><p className="preserve-lines">{student.bio || 'This student is still writing their story.'}</p><h3>Skills</h3><Tags values={student.skills}/><h3>Interests</h3><Tags values={student.interests}/><dl className="facts"><div><dt>Domain</dt><dd>{student.domain}</dd></div><div><dt>Experience</dt><dd>{student.experience}</dd></div><div><dt>Project preference</dt><dd>{student.preferred_project_type}</dd></div><div><dt>Availability</dt><dd>{student.availability_hours} hours / week</dd></div><div><dt>Projects completed</dt><dd>{student.projects_completed}</dd></div></dl>{student.github && <a href={student.github} target="_blank" rel="noreferrer">Visit portfolio ↗</a>}{student.phone && <p>Contact: {student.phone}</p>}</section>
    <aside>{id === user.id ? <Link className="button primary" to="/profile">Edit my profile</Link> : <><StudentCard student={student} onChanged={state.reload}/>{student.connection?.status === 'Accepted' && <ActionButton className="primary wide" action={async () => { const { data } = await api.post('/conversations/', { recipient_id: id }); navigate('/chat/' + data.id); }}>Start a conversation</ActionButton>}</>}<section className="card tip"><h3>Make a thoughtful introduction.</h3><p>Connect first, then discuss your project goals and availability together.</p></section></aside></div></>;
}
