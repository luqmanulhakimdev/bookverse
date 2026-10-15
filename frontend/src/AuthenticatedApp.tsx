import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import App from './App';
import { AuthProvider, useAuth } from './auth';
import { AuthPage, BookDetailPage, LibraryPage, ProfilePage, RecommendationsPage } from './pages';

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1 } } });

function Protected({ children }: { children: ReactNode }) {
  const { token, ready } = useAuth();
  const location = useLocation();
  if (!ready) return <div className="full-state" role="status">Checking your session…</div>;
  if (!token) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return children;
}

function AppRoutes() {
  return <Routes>
    <Route path="/" element={<App />} />
    <Route path="/books/:bookId" element={<BookDetailPage />} />
    <Route path="/login" element={<AuthPage mode="login" />} />
    <Route path="/register" element={<AuthPage mode="register" />} />
    <Route path="/library" element={<Protected><LibraryPage /></Protected>} />
    <Route path="/recommendations" element={<Protected><RecommendationsPage /></Protected>} />
    <Route path="/profile" element={<Protected><ProfilePage /></Protected>} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>;
}

export default function AuthenticatedApp() {
  return <QueryClientProvider client={queryClient}><AuthProvider><BrowserRouter><AppRoutes /></BrowserRouter></AuthProvider></QueryClientProvider>;
}
