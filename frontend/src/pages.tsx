import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useAuth } from './auth';

type Source = { provider: string; external_id: string; source_url?: string | null; access_type: string; access_url?: string | null; rights?: string | null };
type Book = { id: string; title: string; authors: string[]; genres?: string[]; description?: string | null; language?: string | null; published_year?: number | null; cover_url?: string | null; sources?: Source[]; source?: string; source_url?: string | null; access_type?: string; access_url?: string | null; score?: number; reasons?: string[]; status?: string; rating?: number | null; progress?: number | null };
const providerName = (key: string) => key === 'open_library' ? 'Open Library' : key === 'google_books' ? 'Google Books' : key === 'gutenberg' ? 'Project Gutenberg' : key;

export function Navigation() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const logout = async () => { await signOut(); navigate('/'); };
  return <header className="site-header"><Link className="brand" to="/"><span className="brand-icon">B</span> book<span>verse</span></Link><nav aria-label="Main navigation"><Link to="/">Discover</Link><Link to="/recommendations">For you</Link>{user && <Link to="/library">My shelf</Link>}</nav><div className="nav-account">{user ? <><Link to="/profile">{user.email}</Link><button onClick={logout}>Sign out</button></> : <><Link to="/login">Sign in</Link><Link className="signup-link" to="/register">Create account</Link></>}</div></header>;
}

function PageLayout({ children }: { children: ReactNode }) {
  return <div className="app-shell"><Navigation/><main className="content-page">{children}</main><footer><Link className="brand" to="/"><span className="brand-icon">B</span> book<span>verse</span></Link><span>Catalog data belongs to its respective sources.</span></footer></div>;
}

function Cover({ book }: { book: Book }) {
  return <Link className="cover" to={`/books/${book.id}`} aria-label={`View ${book.title} details`}>
    {book.cover_url ? <img src={book.cover_url} alt={`Cover of ${book.title}`} loading="lazy"/> : <span className="no-cover">BOOK<br/>VERSE</span>}
  </Link>;
}

function ProgressControl({ book, onSave }: { book: Book; onSave: (progress: number | null) => void }) {
  const [value, setValue] = useState(book.progress ?? '');
  useEffect(() => setValue(book.progress ?? ''), [book.progress]);
  return <label>Progress % <input aria-label={`Progress for ${book.title}`} type="number" min="0" max="100" value={value} onChange={event => setValue(event.target.value)} onBlur={() => {
    const progress = value === '' ? null : Number(value);
    if (progress !== (book.progress ?? null)) onSave(progress);
  }}/></label>;
}

function BookRow({ book, children }: { book: Book; children?: ReactNode }) {
  return <article className="book-card transition-shadow duration-200"><Cover book={book}/><div className="book-info"><div className="source">{book.sources?.length ? book.sources.map(s => providerName(s.provider)).join(' · ') : providerName(book.source || '')}</div><h3><Link to={`/books/${book.id}`}>{book.title}</Link></h3><p className="author">{book.authors?.join(', ') || 'Author unknown'}</p>{book.published_year && <p className="year">{book.published_year}{book.language ? ` · ${book.language.toUpperCase()}` : ''}</p>}{book.score !== undefined && <div className="recommendation-reasons"><strong>{Math.round(book.score * 100)}% match</strong><span>{book.reasons?.join(' · ')}</span></div>}{children}</div></article>;
}

export function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const register = mode === 'register';
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      await signIn(email, password, register);
      navigate((location.state as { from?: string } | null)?.from || '/profile', { replace: true });
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not sign in.'); }
    finally { setBusy(false); }
  }
  return <PageLayout><section className="auth-panel"><div className="eyebrow">YOUR BOOKSHELF, YOUR WAY</div><h1>{register ? 'Join BookVerse' : 'Welcome back'}</h1><p>{register ? 'Create an account to save books and get thoughtful recommendations.' : 'Sign in to pick up where your reading journey left off.'}</p><form onSubmit={submit} className="auth-form"><label htmlFor="email">Email address</label><input id="email" type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} required/><label htmlFor="password">Password</label><input id="password" type="password" autoComplete={register ? 'new-password' : 'current-password'} minLength={10} maxLength={128} value={password} onChange={e => setPassword(e.target.value)} required/><small>{register ? 'Use at least 10 characters.' : 'Your password is never stored in your browser.'}</small>{error && <p role="alert" className="form-error">{error}</p>}<button className="primary-button" disabled={busy}>{busy ? 'Please wait…' : register ? 'Create account' : 'Sign in'} <span>→</span></button></form><p className="auth-switch">{register ? 'Already a member?' : 'New to BookVerse?'} <Link to={register ? '/login' : '/register'}>{register ? 'Sign in' : 'Create an account'}</Link></p></section></PageLayout>;
}

export function BookDetailPage() {
  const { bookId = '' } = useParams();
  const { token, apiFetch } = useAuth();
  const [notice, setNotice] = useState('');
  const query = useQuery({ queryKey: ['book', bookId], queryFn: () => fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/books/${bookId}`).then(async response => { if (!response.ok) throw new Error('Book details could not be loaded.'); return response.json(); }) });
  const book = query.data as Book | undefined;
  const similar = useQuery({ queryKey: ['similar', bookId], enabled: !!book, queryFn: () => fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/books/${bookId}/similar`).then(async response => { if (!response.ok) throw new Error('Similar books could not be loaded.'); return response.json(); }) });
  const save = async () => { try { await apiFetch(`/api/v1/library/${bookId}`, { method: 'PUT', body: JSON.stringify({ status: 'want_to_read' }) }); setNotice('Saved to your shelf.'); } catch (e) { setNotice(e instanceof Error ? e.message : 'Could not save book.'); } };
  return <PageLayout><Link className="back-link" to="/">← Back to discovery</Link>{query.isLoading ? <div className="full-state" role="status">Loading book details…</div> : query.isError || !book ? <div className="message error" role="alert">{(query.error as Error)?.message || 'Book not found.'}</div> : <><section className="detail-layout"><div className="detail-cover">{book.cover_url ? <img src={book.cover_url} alt={`Cover of ${book.title}`}/> : <span className="no-cover">BOOK<br/>VERSE</span>}</div><div className="detail-copy"><div className="eyebrow">BOOK DETAILS</div><h1>{book.title}</h1><p className="detail-author">{book.authors?.join(', ') || 'Author unknown'}</p><p className="year">{book.published_year || 'Publication year unknown'}{book.language ? ` · ${book.language.toUpperCase()}` : ''}</p>{book.description && <p className="description">{book.description}</p>}{book.genres?.length ? <div className="genre-list">{book.genres.slice(0, 8).map(genre => <span key={genre}>{genre}</span>)}</div> : null}<div className="detail-actions">{token ? <button className="primary-button" onClick={save}>Add to my shelf <span>＋</span></button> : <Link className="primary-button" to="/login">Sign in to save this book</Link>}{notice && <span role="status">{notice}</span>}</div></div></section><section className="availability"><div className="eyebrow">SOURCES & READING OPTIONS</div><h2>Explore at the source</h2>{book.sources?.length ? <div className="source-options">{book.sources.map(source => <article key={`${source.provider}-${source.external_id}`}><strong>{providerName(source.provider)}</strong><span className="access-pill">{source.access_type === 'preview' ? 'Preview' : source.access_type === 'read' ? 'Read online' : source.access_type === 'borrow' ? 'Borrow' : source.access_type === 'download' ? 'External ebook file' : 'Catalog record'}</span>{source.rights && <p className="rights-note">{source.rights}</p>}<a href={source.source_url || source.access_url || '#'} target="_blank" rel="noreferrer">Open source ↗</a></article>)}</div> : <p className="message">No source links are available yet.</p>}</section>{similar.data?.items?.length > 0 && <section className="similar-section"><div className="eyebrow">IF THIS ONE CAUGHT YOUR EYE</div><h2>Similar books</h2><div className="grid">{similar.data.items.map((item: Book) => <BookRow key={item.id} book={item}/>)}</div></section>}</>}</PageLayout>;
}

export function LibraryPage() {
  const { apiFetch } = useAuth();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ['library'], queryFn: () => apiFetch('/api/v1/library') });
  const mutation = useMutation({ mutationFn: ({ id, status, rating, progress }: { id: string; status: string; rating: number | null; progress: number | null }) => apiFetch(`/api/v1/library/${id}`, { method: 'PUT', body: JSON.stringify({ status, rating, progress }) }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['library'] }) });
  const remove = useMutation({ mutationFn: (id: string) => apiFetch(`/api/v1/library/${id}`, { method: 'DELETE' }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['library'] }) });
  return <PageLayout><div className="page-heading"><div className="eyebrow">YOUR PERSONAL COLLECTION</div><h1>My bookshelf</h1><p>Keep track of what you want to read, what you're reading, and what you've finished.</p></div>{query.isLoading ? <div className="full-state" role="status">Loading your shelf…</div> : query.isError ? <div className="message error" role="alert">Could not load your bookshelf. <button onClick={() => query.refetch()}>Try again</button></div> : query.data.items.length === 0 ? <div className="welcome"><div className="welcome-art">✳</div><div><strong>Your shelf is waiting.</strong><p>Explore books and save one to start your personal library.</p><Link to="/">Discover books →</Link></div></div> : <><p className="count">{query.data.count} {query.data.count === 1 ? 'book' : 'books'}</p><div className="grid">{query.data.items.map((book: Book) => <BookRow key={book.id} book={book}><div className="library-controls"><label>Status <select value={book.status} onChange={e => mutation.mutate({ id: book.id, status: e.target.value, rating: book.rating ?? null, progress: book.progress ?? null })}><option value="want_to_read">Want to read</option><option value="reading">Reading</option><option value="finished">Finished</option></select></label><label>Rating <select aria-label={`Rating for ${book.title}`} value={book.rating ?? ''} onChange={e => mutation.mutate({ id: book.id, status: book.status || 'want_to_read', rating: e.target.value ? Number(e.target.value) : null, progress: book.progress ?? null })}><option value="">Not rated</option>{[1, 2, 3, 4, 5].map(value => <option key={value} value={value}>{value} / 5</option>)}</select></label><ProgressControl book={book} onSave={progress => mutation.mutate({ id: book.id, status: book.status || 'want_to_read', rating: book.rating ?? null, progress })}/><button onClick={() => remove.mutate(book.id)}>Remove</button></div></BookRow>)}</div></>}{(mutation.isError || remove.isError) && <p role="alert" className="form-error">{(mutation.error || remove.error)?.message}</p>}</PageLayout>;
}

export function RecommendationsPage() {
  const { apiFetch } = useAuth();
  const query = useQuery({ queryKey: ['recommendations'], queryFn: () => apiFetch('/api/v1/recommendations') });
  return <PageLayout><div className="page-heading"><div className="eyebrow">A LITTLE MORE LIKE WHAT YOU LOVE</div><h1>Picked for you</h1><p>Transparent recommendations based on the books you've rated or read.</p></div>{query.isLoading ? <div className="full-state" role="status">Finding your next read…</div> : query.isError ? <div className="message error" role="alert">Could not load recommendations. <button onClick={() => query.refetch()}>Try again</button></div> : query.data.items.length === 0 ? <div className="welcome"><div className="welcome-art">✳</div><div><strong>Build a little reading history.</strong><p>{query.data.message || 'Rate, read, or finish a book in your library and we can suggest similar titles.'}</p><Link to="/library">Go to my shelf →</Link></div></div> : <div className="grid">{query.data.items.map((book: Book) => <BookRow key={book.id} book={book}><Link className="source-link" to={`/books/${book.id}`}>Explore this book →</Link></BookRow>)}</div>}</PageLayout>;
}

export function ProfilePage() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const logout = async () => { await signOut(); navigate('/'); };
  return <PageLayout><div className="page-heading"><div className="eyebrow">YOUR BOOKVERSE ACCOUNT</div><h1>Reader profile</h1><p>Your account details and reading spaces.</p></div><section className="profile-card"><div className="profile-avatar">{user?.email.slice(0, 1).toUpperCase()}</div><div><div className="eyebrow">SIGNED IN AS</div><h2>{user?.email}</h2><p>Your personal library and recommendations are private to your account.</p></div></section><div className="profile-links"><Link to="/library">Open my bookshelf →</Link><Link to="/recommendations">See my recommendations →</Link><button onClick={logout}>Sign out</button></div></PageLayout>;
}
