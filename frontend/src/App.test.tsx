import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it } from 'vitest';
import App from './App';

describe('discovery home', () => {
  it('shows an accessible search field and an actionable empty prompt', () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><App /></QueryClientProvider>);
    expect(screen.getByLabelText('Search books and authors')).toBeInTheDocument();
    expect(screen.getByText('Follow a curiosity.')).toBeInTheDocument();
  });
});
