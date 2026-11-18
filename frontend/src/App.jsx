import { Component, useEffect, useRef, useState } from 'react';
import { Link, NavLink, Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  BriefcaseBusiness,
  HeartHandshake,
  CalendarDays,
  MessageCircle,
  FolderHeart,
  Settings,
  UserRound,
  LogOut,
  Menu,
  X,
} from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Avatar, ErrorBox } from './components/UI';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import ProfilePage from './pages/ProfilePage';
import StudentsPage, { StudentDetailPage } from './pages/StudentsPage';
import ConnectionsPage from './pages/ConnectionsPage';
import ProjectsPage, { ProjectFormPage } from './pages/ProjectsPage';
import ProjectDetailPage from './pages/ProjectDetailPage';
import MySpacePage from './pages/MySpacePage';
import EventsPage, { ActivityDetailPage } from './pages/EventsPage';
import ChatPage from './pages/ChatPage';
import SettingsPage from './pages/SettingsPage';

const navigation = [
  ['/', 'Overview', LayoutDashboard],
  ['/students', 'Students', Users],
  ['/projects', 'Projects', BriefcaseBusiness],
  ['/connections', 'Connections', HeartHandshake],
  ['/my-space', 'My space', FolderHeart],
  ['/events', 'Events', CalendarDays],
  ['/chat', 'Messages', MessageCircle],
];
class ErrorBoundary extends Component {
  state = { error: false };
  static getDerivedStateFromError() {
    return { error: true };
  }
  render() {
    return this.state.error ? (
      <div className="empty">
        <h1>Something went wrong.</h1>
        <p>Please reload the page to try again.</p>
        <button onClick={() => window.location.reload()}>Reload</button>
      </div>
    ) : (
      this.props.children
    );
  }
}
function Shell() {
  const { user, profile, loading, error, retry, logout } = useAuth(),
    [open, setOpen] = useState(false),
    location = useLocation(),
    menuButton = useRef(null);
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);
  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') {
        setOpen(false);
        menuButton.current?.focus();
      }
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [open]);
  if (loading)
    return (
      <div className="boot-screen">
        <div className="brand">
          connec<span>T</span>
          <small>AI</small>
        </div>
        <p>Getting your campus ready…</p>
        <small>A free backend may take about a minute to wake up.</small>
      </div>
    );
  if (error)
    return (
      <div className="boot-screen">
        <h1>We couldn't reach your campus.</h1>
        <ErrorBox message={error} retry={retry} />
      </div>
    );
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <div className="mobile-header">
        <Link className="brand" to="/">
          connec<span>T</span>
          <small>AI</small>
        </Link>
        <button
          ref={menuButton}
          aria-label="Toggle navigation"
          aria-controls="site-navigation"
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          <Menu size={21} />
        </button>
      </div>
      {open && (
        <button
          className="nav-overlay"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        />
      )}
      <aside id="site-navigation" className={'sidebar ' + (open ? 'open' : '')}>
        <button
          className="nav-close subtle"
          aria-label="Close menu"
          onClick={() => {
            setOpen(false);
            menuButton.current?.focus();
          }}
        >
          <X size={19} />
        </button>
        <Link className="brand" to="/" onClick={() => setOpen(false)}>
          connec<span>T</span>
          <small>AI</small>
        </Link>
        <p className="sidebar-caption">Workspace</p>
        <nav aria-label="Main navigation">
          {navigation.map(([to, label, Icon]) => (
            <NavLink end={to === '/'} key={to} to={to} onClick={() => setOpen(false)}>
              <Icon size={19} />
              {label}
            </NavLink>
          ))}
        </nav>
        <nav className="account-nav" aria-label="Account navigation">
          <NavLink to="/profile" onClick={() => setOpen(false)}>
            <UserRound size={19} />
            My profile
          </NavLink>
          <NavLink to="/settings" onClick={() => setOpen(false)}>
            <Settings size={19} />
            Settings
          </NavLink>
        </nav>
        <div className="account">
          <Avatar name={user.name} />
          <div>
            <strong>{user.name}</strong>
            <small>{profile?.organization_name || profile?.branch || 'Community member'}</small>
          </div>
          <button className="subtle" aria-label="Sign out" onClick={logout}>
            <LogOut size={18} />
          </button>
        </div>
      </aside>
      <main id="main-content" className="main-content">
        <div className="topbar">
          <span>University workspace</span>
          <Link to="/profile">
            <Avatar name={user.name} />
            <span>{user.name.split(' ')[0]}</span>
          </Link>
        </div>
        <div className="page-content">
          <Outlet />
        </div>
        <footer className="page-footer">connecT AI · University collaboration</footer>
      </main>
      <datalist id="project-types">
        {[
          'Web Application',
          'AI/ML Application',
          'Data Analysis',
          'Mobile Application',
          'Backend Service',
          'Security Tool',
          'Cloud Platform',
        ].map((type) => (
          <option key={type} value={type} />
        ))}
      </datalist>
    </div>
  );
}
export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<AuthPage />} />
          <Route path="/register" element={<AuthPage register />} />
          <Route element={<Shell />}>
            <Route index element={<DashboardPage />} />
            <Route path="/recommendations" element={<DashboardPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/students" element={<StudentsPage />} />
            <Route path="/students/:id" element={<StudentDetailPage />} />
            <Route path="/connections" element={<ConnectionsPage />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/projects/new" element={<ProjectFormPage />} />
            <Route path="/projects/:id" element={<ProjectDetailPage />} />
            <Route path="/projects/:id/edit" element={<ProjectFormPage />} />
            <Route path="/my-space" element={<MySpacePage />} />
            <Route path="/events" element={<EventsPage />} />
            <Route path="/events/:id" element={<ActivityDetailPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/chat/:id" element={<ChatPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route
              path="*"
              element={
                <div className="empty">
                  <h1>This page wandered off.</h1>
                  <Link to="/">Back to your overview →</Link>
                </div>
              }
            />
          </Route>
        </Routes>
      </AuthProvider>
    </ErrorBoundary>
  );
}
