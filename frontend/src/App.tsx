import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

type Book = { id: string; title: string; authors: string[]; description?: string | null; language?: string | null; published_year?: number | null; cover_url?: string | null; source: string; source_url?: string | null; access_type: string; access_url?: string | null };
type Result = { items: Book[]; providers: { provider: string; status: string }[]; fetched_count: number };
const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function useDebounced(value: string, delay = 350) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => { const timer = window.setTimeout(() => setDebounced(value), delay); return () => window.clearTimeout(timer); }, [value, delay]);
  return debounced;
}

function App() {
  const [query, setQuery] = useState('');
  const [provider, setProvider] = useState('');
  const [page, setPage] = useState(1);
  const debounced = useDebounced(query);
  useEffect(() => setPage(1), [debounced, provider]);
  const results = useQuery({
    queryKey: ['books', debounced, provider, page], enabled: debounced.trim().length >= 2,
    queryFn: async (): Promise<Result> => {
      const params = new URLSearchParams({ q: debounced.trim(), page: String(page), limit: '20' });
      if (provider) params.set('provider', provider);
      const response = await fetch(`${API}/api/v1/books?${params}`);
      if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail?.message || 'Search is temporarily unavailable.'); }
      return response.json();
    },
  });
  return <div className="app-shell">
    <header><a className="brand" href="#top"><span className="brand-icon">B</span> book<span>verse</span></a><nav aria-label="Main navigation"><a href="#discover">Discover</a><a href="#about">About</a></nav><span className="nav-note">A world of stories, one search away</span></header>
    <main id="top">
      <section className="hero"><div className="eyebrow"><span /> YOUR NEXT CHAPTER STARTS HERE</div><h1>Find the book<br/>that <em>finds you.</em></h1><p>Explore millions of titles across the world's great libraries and catalogs.</p>
        <form className="search" onSubmit={e => e.preventDefault()} role="search"><span aria-hidden="true">⌕</span><label className="sr-only" htmlFor="book-search">Search books and authors</label><input id="book-search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search by title, author, or ISBN…"/><select aria-label="Filter by catalog" value={provider} onChange={e => setProvider(e.target.value)}><option value="">All catalogs</option><option value="open_library">Open Library</option><option value="google_books">Google Books</option></select><button aria-label="Search books">Explore <b>→</b></button></form>
        <div className="popular"><span>TRY SEARCHING</span>{['The Hobbit', 'Ursula Le Guin', 'poetry'].map(item => <button key={item} onClick={() => setQuery(item)}>{item}</button>)}</div>
      </section>
      <section className="results" id="discover"><div className="section-heading"><div><div className="eyebrow">THE DISCOVERY SHELF</div><h2>{debounced ? `Results for “${debounced}”` : 'A little inspiration'}</h2></div>{results.data && <span className="count">{results.data.fetched_count} books found</span>}</div>
        {!debounced.trim() && <div className="welcome"><div className="welcome-art">✳</div><div><strong>Follow a curiosity.</strong><p>Search by title, author, or a subject you love to find your next read.</p></div></div>}
        {debounced.trim().length === 1 && <p className="message">Type at least 2 characters to search.</p>}
        {results.isFetching && <div className="grid" aria-label="Loading results">{Array.from({length: 4}, (_, i) => <div className="skeleton" key={i}><div/><span/><span/></div>)}</div>}
        {results.isError && <div className="message error" role="alert">{(results.error as Error).message} <button onClick={() => results.refetch()}>Try again</button></div>}
        {results.data && !results.data.items.length && <div className="message">No books found. Try a broader title, author, or topic.</div>}
        {results.data && results.data.items.length > 0 && <><div className="grid">{results.data.items.map(book => <article className="book-card" key={`${book.source}-${book.id}`}>
          <a className="cover" href={book.source_url || '#'} target="_blank" rel="noreferrer" aria-label={`View ${book.title} at ${book.source}`}>{book.cover_url ? <img src={book.cover_url} alt={`Cover of ${book.title}`} loading="lazy"/> : <span className="no-cover">BOOK<br/>VERSE</span>}<span className="access-tag">{book.access_type === 'read' ? 'Read online' : book.access_type === 'borrow' ? 'Borrow' : book.access_type === 'preview' ? 'Preview' : 'Catalog'}</span></a>
          <div className="book-info"><div className="source">{book.source === 'open_library' ? 'OPEN LIBRARY' : 'GOOGLE BOOKS'}</div><h3>{book.title}</h3><p className="author">{book.authors.join(', ') || 'Author unknown'}</p>{book.published_year && <p className="year">{book.published_year}{book.language ? ` · ${book.language.toUpperCase()}` : ''}</p>}<a className="source-link" href={book.access_url || book.source_url || '#'} target="_blank" rel="noreferrer">{book.access_type === 'preview' ? 'Open preview ↗' : book.access_type === 'read' ? 'Read at source ↗' : 'View catalog record ↗'}</a></div>
        </article>)}</div><div className="pagination"><span>Provider totals can vary; showing fetched results.</span><div><button disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}>← Previous</button><span>Page {page}</span><button onClick={() => setPage(p => p + 1)}>Next →</button></div></div></>}
        {results.data?.providers.some(p => p.status === 'error') && <p className="provider-note">Some catalogs could not be reached. Results shown are from available sources.</p>}
      </section>
      <section className="trust" id="about"><span>ONE SEARCH, MANY SHELVES</span><div><strong>Open Library</strong><i>·</i><strong>Google Books</strong></div><p>BookVerse brings trusted public catalogs together so you can compare records and explore reading options at their source.</p></section>
    </main><footer><a className="brand" href="#top"><span className="brand-icon">B</span> book<span>verse</span></a><span>Built for the love of finding your next favorite.</span><span>Catalog data belongs to its respective sources.</span></footer>
  </div>;
}

export default App;
