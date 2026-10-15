import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { AuthProvider } from './auth';

describe('discovery home', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: { message: 'No session' } }), { status: 401 })));
  });
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

  function renderHome() {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(<QueryClientProvider client={client}><AuthProvider><MemoryRouter><App /></MemoryRouter></AuthProvider></QueryClientProvider>);
  }

  it('shows an accessible search field and an actionable empty prompt', () => {
    renderHome();
    expect(screen.getByLabelText('Search books and authors')).toBeInTheDocument();
    expect(screen.getByText('Follow a curiosity.')).toBeInTheDocument();
  });

  it('searches the real API contract and links to internal book details', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/api/v1/auth/refresh')) return new Response('{}', { status: 401 });
      return new Response(JSON.stringify({ items: [{ id: 'book-uuid', title: 'A Real Result', authors: ['A. Writer'], source: 'google_books', source_url: 'https://books.google.com', access_type: 'preview', access_url: 'https://books.google.com/preview' }], providers: [{ provider: 'google_books', status: 'ok' }], fetched_count: 1 }), { status: 200 });
    }));
    renderHome();
    fireEvent.change(screen.getByLabelText('Search books and authors'), { target: { value: 'real title' } });
    expect(await screen.findByText('A Real Result')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Book details →' })).toHaveAttribute('href', '/books/book-uuid');
    expect(screen.getByRole('link', { name: 'Open preview ↗' })).toHaveAttribute('href', 'https://books.google.com/preview');
  });

  it('shows a friendly empty result state', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => String(input).endsWith('/api/v1/auth/refresh')
      ? new Response('{}', { status: 401 })
      : new Response(JSON.stringify({ items: [], providers: [], fetched_count: 0 }), { status: 200 })));
    renderHome();
    fireEvent.change(screen.getByLabelText('Search books and authors'), { target: { value: 'no such book' } });
    expect(await screen.findByText('No books found. Try a broader title, author, or topic.')).toBeInTheDocument();
  });
});
