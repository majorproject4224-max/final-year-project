import { useEffect, useRef, useState } from 'react';
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ArrowRight, BriefcaseBusiness, CalendarDays, Check, Compass, LogOut, MessageCircle, Plus, Send, Sparkles, UserRoundPlus, UsersRound } from 'lucide-react';
import { api, authenticatedRequest, clearTokens, getErrorMessage, saveTokens } from './api.js';

const emptyProfile = {
  name: '', branch: '', academic_year: '', skills: '', interests: '', domain: '',
  experience: '', preferred_project_type: '', city: '', phone: '', github: '', share_contact: false,
};

function isOwnMessage(message, currentUserId) {
  return currentUserId != null && String(message.sender_id) === String(currentUserId);
}

function AuthPage({ onAuthenticated }) {
  const [mode, setMode] = useState('login');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [databaseStatus, setDatabaseStatus] = useState('checking');
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/health/ready/')
      .then(() => setDatabaseStatus('ready'))
      .catch((requestError) => setDatabaseStatus(getErrorMessage(requestError)));
  }, []);

  async function submit(event) {
    event.preventDefault();
    setError('');
    setBusy(true);
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    try {
      const response = await api.post(`/auth/${mode}/`, payload);
      saveTokens(response.data.tokens);
      try {
        const { data: savedProfile } = await authenticatedRequest({ url: '/profiles/me/' });
        onAuthenticated(response.data.user, savedProfile);
        navigate('/', { replace: true });
      } catch (profileError) {
        if (profileError.response?.status === 404) {
          onAuthenticated(response.data.user, null);
          navigate('/profile', { replace: true });
        } else {
          throw profileError;
        }
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  return <main className="auth-page">
    <section className="auth-copy">
      <div className="brand-mark">c<span>.</span></div>
      <p className="kicker">UNIVERSITY, IN MOTION</p>
      <h1>Good projects<br />start with<br /><em>good people.</em></h1>
      <p className="auth-note">Find collaborators who bring a different strength to the same idea.</p>
      <div className="auth-stamp"><Sparkles size={17} /> Profile-led matching, built for campus teams</div>
    </section>
    <section className="auth-form-wrap">
      <div className="auth-form-head"><span>{mode === 'login' ? 'Welcome back' : 'Create your account'}</span><div className="mode-switch"><button className={mode === 'login' ? 'selected' : ''} onClick={() => setMode('login')} type="button">Sign in</button><button className={mode === 'register' ? 'selected' : ''} onClick={() => setMode('register')} type="button">Join</button></div></div>
      <form className="auth-form" onSubmit={submit}>
        {mode === 'register' && <label>Your name<input name="name" autoComplete="name" required maxLength="80" /></label>}
        <label>University email<input name="email" type="email" autoComplete="email" required /></label>
        <label>Password<input name="password" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength="8" required /></label>
        {databaseStatus !== 'ready' && <p className="notice warning">{databaseStatus === 'checking' ? 'Checking database connection…' : databaseStatus}</p>}
        {error && <p className="notice error">{error}</p>}
        <button className="primary-button" disabled={busy}>{busy ? 'Working…' : mode === 'login' ? 'Sign in' : 'Create account'}<ArrowRight size={17} /></button>
        <p className="fine-print">By continuing, you agree to use connecT AI for respectful academic collaboration.</p>
      </form>
    </section>
  </main>;
}

function ProfilePage({ onComplete, initialName }) {
  const [profile, setProfile] = useState({ ...emptyProfile, name: initialName || '' });
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [resume, setResume] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    authenticatedRequest({ url: '/profiles/me/' }).then(({ data }) => {
      setProfile({ ...emptyProfile, ...data, skills: data.skills?.join(', ') || '', interests: data.interests?.join(', ') || '' });
    }).catch((requestError) => {
      if (requestError.response?.status !== 404) setError(getErrorMessage(requestError));
    });
  }, []);

  function update(event) {
    const { name, value, checked, type } = event.target;
    setProfile((current) => ({ ...current, [name]: type === 'checkbox' ? checked : value }));
  }

  async function analyzeResume(event) {
    event.preventDefault();
    if (!resume) return setError('Choose a PDF or DOCX resume first.');
    setError('');
    setMessage('');
    const payload = new FormData();
    payload.append('resume', resume);
    try {
      const { data } = await authenticatedRequest({ method: 'post', url: '/profiles/resume-suggestions/', data: payload });
      setProfile((current) => {
        const next = { ...current };
        for (const [key, value] of Object.entries(data.suggestions)) {
          if (value && !next[key]) next[key] = Array.isArray(value) ? value.join(', ') : value;
        }
        return next;
      });
      setMessage('Suggestions added. Review every field before saving.');
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    }
  }

  async function saveProfile(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    const payload = {
      ...profile,
      academic_year: Number(profile.academic_year),
      skills: profile.skills.split(',').map((value) => value.trim()).filter(Boolean),
      interests: profile.interests.split(',').map((value) => value.trim()).filter(Boolean),
    };
    try {
      const { data } = await authenticatedRequest({ method: 'put', url: '/profiles/me/', data: payload });
      onComplete(data);
      navigate('/', { replace: true });
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  return <div className="page narrow-page">
    <div className="page-heading"><p className="kicker">YOUR STARTING POINT</p><h1>Build your profile.</h1><p>Tell people what you know, what you want to learn, and what you hope to make.</p></div>
    <section className="resume-panel"><div><span className="resume-icon"><Sparkles size={19} /></span><div><h2>Start with your resume</h2><p>We’ll suggest details, then you review them. Your file is not stored.</p></div></div><form className="resume-upload" onSubmit={analyzeResume}><input type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(event) => setResume(event.target.files?.[0] || null)} /><button type="submit" className="secondary-button">Analyze resume</button></form></section>
    {message && <p className="notice success">{message}</p>}{error && <p className="notice error">{error}</p>}
    <form className="profile-form" onSubmit={saveProfile}>
      <div className="form-section-title"><span>01</span><h2>About you</h2></div>
      <div className="field-grid">
        <label>Name<input name="name" value={profile.name} onChange={update} required maxLength="80" /></label>
        <label>Branch<input name="branch" value={profile.branch} onChange={update} placeholder="Computer Science and Engineering" required /></label>
        <label>Academic year<select name="academic_year" value={profile.academic_year} onChange={update} required><option value="">Select year</option>{[1, 2, 3, 4].map((year) => <option key={year} value={year}>Year {year}</option>)}</select></label>
        <label>City<input name="city" value={profile.city} onChange={update} required /></label>
      </div>
      <div className="form-section-title"><span>02</span><h2>Skills and direction</h2></div>
      <div className="field-grid">
        <label className="span-two">Skills<input name="skills" value={profile.skills} onChange={update} placeholder="Python, React, UI/UX" required /><small>Separate skills with commas.</small></label>
        <label className="span-two">Interests<input name="interests" value={profile.interests} onChange={update} placeholder="Research, open source, product design" required /><small>Separate interests with commas.</small></label>
        <label>Technical domain<select name="domain" value={profile.domain} onChange={update} required><option value="">Choose a domain</option>{['AI / ML', 'Data Science', 'Web Development', 'Mobile Development', 'Backend Development', 'Cybersecurity'].map((domain) => <option key={domain}>{domain}</option>)}</select></label>
        <label>Experience<select name="experience" value={profile.experience} onChange={update} required><option value="">Choose a level</option>{['Beginner', 'Intermediate', 'Advanced'].map((level) => <option key={level}>{level}</option>)}</select></label>
        <label>Preferred project type<input name="preferred_project_type" value={profile.preferred_project_type} onChange={update} placeholder="Web Application" required /></label>
        <label>Phone <span className="optional">optional</span><input name="phone" value={profile.phone} onChange={update} autoComplete="tel" /></label>
        <label className="span-two">GitHub profile <span className="optional">optional</span><input name="github" type="url" value={profile.github} onChange={update} placeholder="https://github.com/username" /></label>
      </div>
      <label className="checkbox-label"><input type="checkbox" name="share_contact" checked={profile.share_contact} onChange={update} /> Share my contact details with recommended teammates</label>
      <div className="form-actions"><span>All fields marked by the form are required before recommendations can be generated.</span><button className="primary-button" disabled={busy}>{busy ? 'Saving…' : 'Save profile'}<ArrowRight size={17} /></button></div>
    </form>
  </div>;
}

function DashboardPage({ profile }) {
  const [recommendations, setRecommendations] = useState([]);
  const [notice, setNotice] = useState('');
  const [projects, setProjects] = useState([]);
  const [projectMatches, setProjectMatches] = useState([]);
  const [connectionStates, setConnectionStates] = useState({});
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      authenticatedRequest({ url: '/recommendations/users/' }),
      authenticatedRequest({ url: '/projects/' }),
      authenticatedRequest({ url: '/projects/recommendations/' }),
      authenticatedRequest({ url: '/connections/' }),
    ]).then(([matches, projectList, projectRecommendations, connectionList]) => {
      setRecommendations(matches.data.items || []);
      setNotice(matches.data.detail || matches.data.model_notice || '');
      setProjects(projectList.data);
      setProjectMatches(projectRecommendations.data.items || []);
      setConnectionStates(Object.fromEntries(connectionList.data.map((connection) => [connection.user_id, connection])));
    }).catch((requestError) => setError(getErrorMessage(requestError)));
  }, []);

  async function connect(userId) {
    const existing = connectionStates[userId];
    if (existing?.status === 'Accepted' || (existing?.status === 'Pending' && existing.direction === 'sent')) return;
    setConnectionStates((current) => ({
      ...current,
      [userId]: { ...existing, status: existing?.direction === 'received' ? 'Accepting' : 'Sending', direction: existing?.direction || 'sent' },
    }));
    try {
      if (existing?.status === 'Pending' && existing.direction === 'received') {
        await authenticatedRequest({ method: 'patch', url: `/connections/${existing.id}/` });
        setConnectionStates((current) => ({ ...current, [userId]: { ...existing, status: 'Accepted' } }));
      } else {
        const { data } = await authenticatedRequest({ method: 'post', url: '/connections/', data: { user_id: userId } });
        setConnectionStates((current) => ({
          ...current,
          [userId]: { id: data.id, user_id: userId, status: 'Pending', direction: 'sent' },
        }));
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError));
      setConnectionStates((current) => ({ ...current, [userId]: existing }));
    }
  }

  return <div className="page dashboard-page">
    <section className="welcome-band"><div><p className="kicker">YOUR COLLABORATION DESK</p><h1>Good to have you,<br /><em>{profile?.name || 'student'}.</em></h1><p>Your next project partner might be one connection away.</p></div><div className="welcome-index"><span>PROFILE</span><strong>{profile?.domain || 'Ready'}</strong><small>{profile?.academic_year ? `Year ${profile.academic_year}` : 'Student'}</small></div></section>
    {error && <p className="notice error">{error}</p>}
    <section className="dashboard-section"><div className="section-heading"><div><p className="kicker">PEOPLE TO BUILD WITH</p><h2><UsersRound size={22} /> Recommended students</h2></div><NavLink to="/profile" className="text-link">Edit profile <ArrowRight size={15} /></NavLink></div>
      {notice && <p className="model-note">{notice}</p>}
      {recommendations.length ? <div className="recommendation-list">{recommendations.map((person, index) => { const connection = connectionStates[person.user_id]; const pendingSent = connection?.status === 'Pending' && connection.direction === 'sent'; const accepted = connection?.status === 'Accepted'; const incoming = connection?.status === 'Pending' && connection.direction === 'received'; const working = connection?.status === 'Sending' || connection?.status === 'Accepting'; const label = accepted ? 'Connected' : pendingSent ? 'Request sent' : incoming ? 'Accept request' : working ? (connection.status === 'Accepting' ? 'Accepting…' : 'Sending…') : 'Connect'; return <article className="recommendation-row" key={person.user_id}><span className="row-number">0{index + 1}</span><div className="person-main"><h3>{person.name}</h3><p>{person.branch} · Year {person.academic_year} · {person.domain}</p><div className="skill-list">{person.skills.slice(0, 5).map((skill) => <span key={skill}>{skill}</span>)}</div>{person.explanations.length > 0 && <p className="explanation">{person.explanations.map((item) => item.feature === 'shared_skills' ? `${item.items.length} shared skill${item.items.length === 1 ? '' : 's'}` : item.feature === 'shared_interests' ? `${item.items.length} common interest${item.items.length === 1 ? '' : 's'}` : item.value).join(' · ')}</p>}<button className={`connect-button ${accepted ? 'connected' : ''}`} disabled={accepted || pendingSent || working} onClick={() => connect(person.user_id)}>{accepted ? <Check size={14} /> : <UserRoundPlus size={14} />}{label}</button></div><strong className="match-score">{person.compatibility_score}<small>%</small></strong></article>; })}</div> : <div className="empty-state"><Compass size={23} /><p>{notice || 'Add your skills and interests to receive student recommendations.'}</p></div>}
    </section>
    <section className="dashboard-section"><div className="section-heading"><div><p className="kicker">OPEN CALLS</p><h2><BriefcaseBusiness size={22} /> Projects looking for people</h2></div><NavLink to="/projects/new" className="icon-link" aria-label="Create a project" title="Create a project"><Plus size={19} /></NavLink></div>
      {projects.length ? <div className="project-list">{projects.map((project) => { const match = projectMatches.find((item) => item.id === project.id); const isOwner = project.owner_id === profile?.user_id; return <article key={project.id} className="project-row"><div><span className="project-domain">{project.domain}</span><h3>{project.title}</h3><p>{project.description}</p><div className="skill-list">{project.required_skills.map((skill) => <span key={skill}>{skill}</span>)}</div><p className="project-team-count">{project.team_member_count}/{project.team_size} team members</p>{match && <p className="explanation">{match.compatibility_score}% profile-to-requirements match</p>}</div>{isOwner ? <NavLink className="secondary-button" to={`/projects/${project.id}/applications/`}>Review applicants <ArrowRight size={14} /></NavLink> : <button className="secondary-button" onClick={async () => { try { await authenticatedRequest({ method: 'post', url: `/projects/${project.id}/applications/`, data: {} }); setNotice('Application sent.'); } catch (requestError) { setError(getErrorMessage(requestError)); } }}>Apply <ArrowRight size={14} /></button>}</article>; })}</div> : <div className="empty-state"><BriefcaseBusiness size={23} /><p>No projects are open yet. Start one for your campus team.</p><NavLink to="/projects/new" className="text-link">Create a project <ArrowRight size={15} /></NavLink></div>}
    </section>
  </div>;
}

function ProjectApplicationsPage() {
  const { projectId } = useParams();
  const [applications, setApplications] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    authenticatedRequest({ url: `/projects/${projectId}/applications/` })
      .then(({ data }) => setApplications(data))
      .catch((requestError) => setError(getErrorMessage(requestError)));
  }, [projectId]);

  async function decide(applicationId, decision) {
    try {
      await authenticatedRequest({
        method: 'patch',
        url: `/projects/${projectId}/applications/`,
        data: { application_id: applicationId, decision },
      });
      setApplications((current) => current.map((application) => application.id === applicationId ? { ...application, status: decision } : application));
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    }
  }

  return <div className="page narrow-page"><div className="page-heading"><p className="kicker">BUILD YOUR TEAM</p><h1>Project applicants.</h1><p>Review each request. Accepting adds the applicant while team capacity remains.</p></div>{error && <p className="notice error">{error}</p>}{applications.length ? <div className="connection-list">{applications.map((application) => <article className="connection-row" key={application.id}><div className="connection-avatar">{application.name.slice(0, 1)}</div><div className="connection-person"><h2>{application.name}</h2><p>Applied {new Date(application.created_at).toLocaleDateString()} · {application.status}</p></div>{application.status === 'Pending' ? <div className="application-actions"><button className="secondary-button" onClick={() => decide(application.id, 'Accepted')}><Check size={14} /> Accept</button><button className="quiet-button" onClick={() => decide(application.id, 'Rejected')}>Decline</button></div> : <span className="pending-label">{application.status}</span>}</article>)}</div> : <div className="empty-state"><UsersRound size={23} /><p>No applications yet. Student requests will appear here.</p></div>}</div>;
}

function ConnectionsPage() {
  const [connections, setConnections] = useState([]);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    authenticatedRequest({ url: '/connections/' })
      .then(({ data }) => setConnections(data))
      .catch((requestError) => setError(getErrorMessage(requestError)));
  }, []);

  async function accept(connectionId) {
    try {
      await authenticatedRequest({ method: 'patch', url: `/connections/${connectionId}/` });
      setConnections((current) => current.map((connection) => connection.id === connectionId ? { ...connection, status: 'Accepted' } : connection));
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    }
  }

  async function message(userId) {
    try {
      const { data } = await authenticatedRequest({ method: 'post', url: '/conversations/', data: { recipient_id: userId } });
      navigate(`/chat?conversation=${data.id}`);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    }
  }

  return <div className="page narrow-page"><div className="page-heading"><p className="kicker">YOUR CAMPUS NETWORK</p><h1>Connections.</h1><p>Requests and accepted collaborators live here.</p></div>{error && <p className="notice error">{error}</p>}{connections.length ? <div className="connection-list">{connections.map((connection) => <article className="connection-row" key={connection.id}><div className="connection-avatar">{connection.name.slice(0, 1)}</div><div className="connection-person"><h2>{connection.name}</h2><p>{connection.direction === 'received' && connection.status === 'Pending' ? 'Wants to connect' : connection.status === 'Pending' ? 'Request sent' : 'Connected'}</p></div>{connection.direction === 'received' && connection.status === 'Pending' ? <button className="secondary-button" onClick={() => accept(connection.id)}><Check size={14} /> Accept</button> : connection.status === 'Accepted' ? <button className="secondary-button" onClick={() => message(connection.user_id)}><MessageCircle size={14} /> Message</button> : <span className="pending-label">Pending</span>}</article>)}</div> : <div className="empty-state"><UsersRound size={23} /><p>Connection requests and accepted students will appear here.</p><NavLink to="/" className="text-link">Discover students <ArrowRight size={15} /></NavLink></div>}</div>;
}

function EventsPage() {
  const [events, setEvents] = useState([]);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      const { data } = await authenticatedRequest({ url: '/events/' });
      setEvents(data);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    }
  }

  useEffect(() => { refresh(); }, []);

  async function createEvent(event) {
    event.preventDefault();
    setBusy(true);
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form).entries());
    values.starts_at = new Date(values.starts_at).toISOString();
    try {
      await authenticatedRequest({ method: 'post', url: '/events/', data: values });
      form.reset();
      setNotice('Event posted.');
      await refresh();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function attend(eventId) {
    try {
      await authenticatedRequest({ method: 'post', url: `/events/${eventId}/attendance/`, data: {} });
      setNotice('You are on the attendee list.');
      await refresh();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    }
  }

  return <div className="page narrow-page"><div className="page-heading"><p className="kicker">CAMPUS CALENDAR</p><h1>Events.</h1><p>Discover meetups, workshops, and student-led activities.</p></div>{error && <p className="notice error">{error}</p>}{notice && <p className="notice success">{notice}</p>}<section className="event-list">{events.map((event) => <article className="event-row" key={event.id}><div className="event-date"><CalendarDays size={19} /><span>{new Date(event.starts_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span></div><div className="event-info"><h2>{event.title}</h2><p>{event.description}</p><small>{event.location} · {new Date(event.starts_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })} · {event.attendee_count} attending</small></div><button className="secondary-button" onClick={() => attend(event.id)}>Attend</button></article>)}{!events.length && <div className="empty-state"><CalendarDays size={23} /><p>No upcoming events yet. Add one for your campus.</p></div>}</section><form className="profile-form event-form" onSubmit={createEvent}><div className="form-section-title"><span>+</span><h2>Post an event</h2></div><label>Event title<input name="title" maxLength="120" required /></label><label>Description<textarea name="description" rows="3" maxLength="2000" required /></label><div className="field-grid"><label>Location<input name="location" required /></label><label>Date and time<input name="starts_at" type="datetime-local" required /></label></div><button className="primary-button" disabled={busy}>{busy ? 'Posting…' : 'Post event'}<ArrowRight size={16} /></button></form></div>;
}

function ChatPage({ currentUserId }) {
  const [conversations, setConversations] = useState([]);
  const [messages, setMessages] = useState([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [activeId, setActiveId] = useState('');
  const [draft, setDraft] = useState('');
  const [error, setError] = useState('');
  const [searchParams, setSearchParams] = useSearchParams();
  const messageListRef = useRef(null);
  const activeIdRef = useRef(activeId);
  activeIdRef.current = activeId;
  const active = conversations.find((conversation) => conversation.id === activeId);

  useEffect(() => {
    const messageList = messageListRef.current;
    if (messageList) messageList.scrollTop = messageList.scrollHeight;
  }, [messages]);

  useEffect(() => {
    authenticatedRequest({ url: '/conversations/' }).then(({ data }) => setConversations(data)).catch((requestError) => setError(getErrorMessage(requestError)));
  }, []);

  useEffect(() => {
    const requestedId = searchParams.get("conversation") || "";
    if (!requestedId || !conversations.length) return;

    const requestedConversation = conversations.find((conversation) => conversation.id === requestedId);
    if (!requestedConversation) {
      activeIdRef.current = "";
      setMessages([]);
      setMessagesLoading(false);
      setActiveId("");
      setSearchParams({}, { replace: true });
      return;
    }

    if (requestedId === activeId) return;
    activeIdRef.current = requestedId;
    setMessages([]);
    setMessagesLoading(true);
    setError("");
    setActiveId(requestedId);
  }, [searchParams, conversations, activeId, setSearchParams]);

  useEffect(() => {
    if (!activeId) return undefined;
    let socket;
    let cancelled = false;
    authenticatedRequest({ url: `/conversations/${activeId}/messages/` }).then(({ data }) => {
      if (!cancelled && activeIdRef.current === activeId) {
        setMessages(data);
        setMessagesLoading(false);
      }
      return authenticatedRequest({ method: 'patch', url: `/conversations/${activeId}/messages/` });
    }).then(() => authenticatedRequest({ method: 'post', url: `/conversations/${activeId}/websocket-ticket/`, data: {} })).then(({ data }) => {
      if (cancelled || activeIdRef.current !== activeId) return;
      const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      socket = new WebSocket(`${scheme}//${window.location.host}/ws/conversations/${activeId}/?ticket=${encodeURIComponent(data.ticket)}`);
      socket.onmessage = (event) => {
        if (cancelled || activeIdRef.current !== activeId) return;
        const payload = JSON.parse(event.data);
        if (payload.type === 'message') {
          const incomingMessage = payload.message;
          setMessages((current) => current.some((item) => item.id === incomingMessage.id) ? current : [...current, incomingMessage]);
          setConversations((current) => current.map((conversation) => conversation.id === activeId
            ? { ...conversation, last_message: incomingMessage.content, updated_at: incomingMessage.created_at }
            : conversation));
        }
      };
      socket.onerror = () => setError('Live chat disconnected. Reload this conversation to reconnect.');
    }).catch((requestError) => {
      if (!cancelled) {
        setMessagesLoading(false);
        setError(getErrorMessage(requestError));
      }
    });
    return () => { cancelled = true; socket?.close(); };
  }, [activeId]);

  async function selectConversation(conversationId) {
    if (conversationId === activeIdRef.current) return;
    setMessages([]);
    setMessagesLoading(true);
    setError('');
    activeIdRef.current = conversationId;
    setActiveId(conversationId);
    setSearchParams({ conversation: conversationId }, { replace: true });
  }

  async function sendMessage(event) {
    event.preventDefault();
    const content = draft.trim();
    const conversationId = activeIdRef.current;
    if (!content || !conversationId) return;
    try {
      const { data } = await authenticatedRequest({ method: 'post', url: `/conversations/${conversationId}/messages/`, data: { content } });
      if (activeIdRef.current === conversationId) {
        setMessages((current) => current.some((item) => item.id === data.id) ? current : [...current, data]);
      }
      setConversations((current) => current.map((conversation) => conversation.id === conversationId
        ? { ...conversation, last_message: data.content, updated_at: data.created_at }
        : conversation));
      setDraft((current) => current === draft ? '' : current);
    } catch (requestError) {
      if (activeIdRef.current === conversationId) setError(getErrorMessage(requestError));
    }
  }

  return <div className="page chat-page"><div className="page-heading"><p className="kicker">PRIVATE CONVERSATIONS</p><h1>Messages.</h1></div>{error && <p className="notice error">{error}</p>}<section className="chat-layout"><aside className="chat-threads">{conversations.map((conversation) => <button key={conversation.id} className={`thread-button ${activeId === conversation.id ? 'active' : ''}`} onClick={() => selectConversation(conversation.id)}><span className="connection-avatar">{conversation.participant_name.slice(0, 1)}</span><span><strong>{conversation.participant_name}</strong><small>{conversation.last_message || 'Start the conversation'}</small></span></button>)}{!conversations.length && <p className="thread-empty">Start a conversation from your connections.</p>}</aside><div className="chat-panel"><header>{active ? <><span className="connection-avatar">{active.participant_name.slice(0, 1)}</span><div><strong>{active.participant_name}</strong><small>Chat history</small></div></> : <span>Select someone from Connections to start messaging</span>}</header><div className="message-list" ref={messageListRef}>{!active ? <p className="thread-empty">Choose an existing conversation, or open Connections and press Message on a connected student.</p> : messagesLoading ? <p className="message-status">Loading chat history…</p> : messages.length ? messages.map((message) => { const sentByMe = isOwnMessage(message, currentUserId); return <article key={message.id} aria-label={`${sentByMe ? 'Sent by you' : `Sent by ${active.participant_name}`}: ${message.content}`} className={`message-bubble ${sentByMe ? 'sent' : 'received'}`}><small className="message-sender">{sentByMe ? 'You' : active.participant_name}</small><p>{message.content}</p><time>{new Date(message.created_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</time></article>; }) : <p className="message-status">No messages yet. Say hello to start the conversation.</p>}</div><form className="message-composer" onSubmit={sendMessage}><input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={active ? 'Write a message…' : 'Choose a conversation'} disabled={!active} maxLength="4000" /><button className="primary-button" aria-label="Send message" disabled={!active || !draft.trim()}><Send size={16} /></button></form></div></section></div>;
}

function CreateProjectPage() {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    payload.required_skills = payload.required_skills.split(',').map((skill) => skill.trim()).filter(Boolean);
    payload.team_size = Number(payload.team_size);
    try {
      await authenticatedRequest({ method: 'post', url: '/projects/', data: payload });
      navigate('/', { replace: true });
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  return <div className="page narrow-page"><div className="page-heading"><p className="kicker">START SOMETHING</p><h1>Post a project.</h1><p>Be clear about the problem and skills your team needs.</p></div>{error && <p className="notice error">{error}</p>}<form className="profile-form project-form" onSubmit={submit}><label>Project title<input name="title" maxLength="100" required /></label><label>Project description<textarea name="description" maxLength="2000" rows="5" required /></label><label>Required skills<input name="required_skills" placeholder="Python, UI/UX, research" required /><small>Separate skills with commas.</small></label><label>Domain<select name="domain" required><option value="">Choose a domain</option>{['AI / ML', 'Data Science', 'Web Development', 'Mobile Development', 'Backend Development', 'Cybersecurity'].map((domain) => <option key={domain}>{domain}</option>)}</select></label><label>Project type<input name="project_type" placeholder="Web Application" required /></label><label>Team size<input name="team_size" type="number" min="2" max="10" defaultValue="4" required /></label><button className="primary-button" disabled={busy}>{busy ? 'Posting…' : 'Post project'}<ArrowRight size={17} /></button></form></div>;
}

function App() {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const hasToken = Boolean(localStorage.getItem('connect.access'));

  useEffect(() => {
    if (!hasToken) {
      setLoaded(true);
      return;
    }
    authenticatedRequest({ url: '/profiles/me/' }).then(({ data }) => {
      setProfile(data);
      setUser({ id: data.user_id, name: data.name });
    }).catch((error) => {
      if (error.response?.status === 404) {
        setUser({ name: error.response.data.name || 'Student' });
        setProfile(null);
      } else {
        clearTokens();
        setUser(null);
        setProfile(null);
      }
    }).finally(() => setLoaded(true));
  }, []);

  function logout() {
    clearTokens();
    setUser(null);
    setProfile(null);
    navigate('/auth', { replace: true });
  }

  if (!loaded) return <div className="loading-screen">connecT<span>.</span></div>;
  if (!user && location.pathname !== '/auth') return <Navigate to="/auth" replace />;
  if (user && location.pathname === '/auth') return <Navigate to={profile ? '/' : '/profile'} replace />;
  if (user && !profile && location.pathname !== '/profile') return <Navigate to="/profile" replace />;

  if (location.pathname === '/auth') return <AuthPage onAuthenticated={(currentUser, currentProfile) => { setUser(currentUser); setProfile(currentProfile); }} />;

  return <div className="app-shell"><aside className="sidebar"><NavLink to="/" className="side-brand">connecT<span>.</span></NavLink><p className="side-label">CAMPUS</p><nav className="side-nav"><NavLink to="/" end><Compass size={18} /> Discover</NavLink><NavLink to="/connections"><UsersRound size={18} /> Connections</NavLink><NavLink to="/chat"><MessageCircle size={18} /> Messages</NavLink><NavLink to="/events"><CalendarDays size={18} /> Events</NavLink><NavLink to="/projects/new"><Plus size={18} /> Post a project</NavLink><NavLink to="/profile"><UsersRound size={18} /> My profile</NavLink></nav><div className="side-bottom"><div className="user-chip"><span className="avatar">{(user?.name || 'S').slice(0, 1).toUpperCase()}</span><span>{user?.name || 'Student'}<small>{profile?.domain || 'Complete profile'}</small></span></div><button className="logout-button" onClick={logout} title="Sign out" aria-label="Sign out"><LogOut size={17} /></button></div></aside><main className="main-content"><Routes><Route path="/" element={<DashboardPage profile={profile} />} /><Route path="/profile" element={<ProfilePage initialName={user?.name} onComplete={(savedProfile) => setProfile(savedProfile)} />} /><Route path="/connections" element={<ConnectionsPage />} /><Route path="/chat" element={<ChatPage currentUserId={user?.id || profile?.user_id} />} /><Route path="/events" element={<EventsPage />} /><Route path="/projects/new" element={<CreateProjectPage />} /><Route path="/projects/:projectId/applications" element={<ProjectApplicationsPage />} /><Route path="*" element={<Navigate to="/" replace />} /></Routes></main></div>;
}

export default App;
