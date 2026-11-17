import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useData } from '../hooks/useData';
import { PageTitle, DataState, Pagination, Avatar, ActionButton } from '../components/UI';
export default function ConnectionsPage() {
  const [page, setPage] = useState(1), state = useData('/connections/?page=' + page), navigate = useNavigate();
  return <><PageTitle eyebrow="YOUR CIRCLE" title="Good things start with a hello." action={<Link className="button primary" to="/students">Find students</Link>}>Manage your connections and requests.</PageTitle>
    <DataState state={state} empty="Your circle starts with one connection. Find a student and say hello."><section className="card list">{state.data?.items.map(person => <div className="list-row" key={person.id}><Avatar name={person.name}/><div className="grow"><Link className="title-link" to={'/students/' + person.user_id}>{person.name}</Link><p className="muted">{person.status} · {person.direction === 'received' ? 'Received request' : 'Sent request'}</p></div>
      {person.status === 'Pending' && person.direction === 'received' && <><ActionButton className="primary" action={() => api.patch('/connections/' + person.id + '/', { action: 'accept' })} onDone={state.reload}>Accept</ActionButton><ActionButton action={() => api.patch('/connections/' + person.id + '/', { action: 'reject' })} onDone={state.reload}>Decline</ActionButton></>}
      {person.status === 'Accepted' && <ActionButton className="primary" action={async () => { const { data } = await api.post('/conversations/', { recipient_id: person.user_id }); navigate('/chat/' + data.id); }}>Message</ActionButton>}
      <ActionButton className="subtle danger" action={async () => { if (window.confirm(person.status === 'Accepted' ? 'Remove this connection? Messaging will stop until you reconnect.' : 'Remove this request?')) await api.delete('/connections/' + person.id + '/'); }} onDone={state.reload}>{person.status === 'Accepted' ? 'Remove' : 'Clear'}</ActionButton>
    </div>)}</section><Pagination data={state.data} page={page} setPage={setPage}/></DataState></>;
}
