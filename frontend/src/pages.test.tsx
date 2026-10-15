import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider } from './auth';
import { BookDetailPage, LibraryPage, RecommendationsPage } from './pages';

const sampleBook = {
  id: 'book-id', title: 'The Example', authors: ['A. Writer'], genres: ['Fantasy'],
  sources: [{ provider: 'gutenberg', external_id: '42', source_url: 'https://www.gutenberg.org/ebooks/42',
    access_type: 'download', access_url: 'https://www.gutenberg.org/files/42/book.epub',
    rights: 'Public domain in the United States; check local laws.' }],
};

function setup(initialPath: string, handler?: (url: string, init?: RequestInit) => Response) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith('/api/v1/auth/refresh')) return new Response('{}', { status: 401 });
    return handler?.(url, init) || new Response(JSON.stringify({ detail: { message: 'Not found' } }), { status: 404 });
  });
  vi.stubGlobal('fetch', fetchMock);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = render(<QueryClientProvider client={client}><AuthProvider><MemoryRouter initialEntries={[initialPath]}><Routes>
    <Route path="/books/:bookId" element={<BookDetailPage/>}/>
    <Route path="/library" element={<LibraryPage/>}/>
    <Route path="/recommendations" element={<RecommendationsPage/>}/>
  </Routes></MemoryRouter></AuthProvider></QueryClientProvider>);
  return { ...view, fetchMock };
}

describe('BookVerse account pages', () => {
  beforeEach(() => vi.unstubAllGlobals());
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

  it('shows book sources, reading access, and rights notes on the internal detail page', async () => {
    setup('/books/book-id', url => url.endsWith('/api/v1/books/book-id')
      ? new Response(JSON.stringify(sampleBook), { status: 200 }) : new Response('{}', { status: 404 }));
    expect(await screen.findByText('The Example')).toBeInTheDocument();
    expect(screen.getByText('External ebook file')).toBeInTheDocument();
    expect(screen.getByText(/check local laws/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open source ↗' })).toHaveAttribute('href', 'https://www.gutenberg.org/ebooks/42');
  });

  it('renders saved books and sends status changes to the library API', async () => {
    const fetchData = (url: string, init?: RequestInit) => {
      if (url.endsWith('/api/v1/library') && !init?.method) return new Response(JSON.stringify({ items: [{ ...sampleBook, status: 'want_to_read', rating: null, progress: null }], count: 1 }), { status: 200 });
      if (url.endsWith('/api/v1/library/book-id') && init?.method === 'PUT') return new Response(JSON.stringify({ status: 'reading' }), { status: 200 });
      if (url.endsWith('/api/v1/library/book-id') && init?.method === 'DELETE') return new Response(null, { status: 204 });
      return new Response('{}', { status: 404 });
    };
    const { fetchMock } = setup('/library', fetchData);
    expect(await screen.findByRole('heading', { name: 'My bookshelf' })).toBeInTheDocument();
    expect(await screen.findByText('The Example')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'reading' } });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/v1/library/book-id'), expect.objectContaining({ method: 'PUT' })));
    fireEvent.click(screen.getByRole('button', { name: 'Remove' }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/v1/library/book-id'), expect.objectContaining({ method: 'DELETE' })));
  });

  it('shows a useful empty state when a user has no recommendation seeds', async () => {
    setup('/recommendations', url => url.endsWith('/api/v1/recommendations')
      ? new Response(JSON.stringify({ items: [], count: 0, message: 'Rate a book to start.' }), { status: 200 })
      : new Response('{}', { status: 404 }));
    expect(await screen.findByRole('heading', { name: 'Picked for you' })).toBeInTheDocument();
    expect(await screen.findByText('Rate a book to start.')).toBeInTheDocument();
  });
});
