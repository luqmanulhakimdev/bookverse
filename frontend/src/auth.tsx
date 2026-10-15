import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export type User = { id: string; email: string };
type AuthState = {
  token: string | null;
  user: User | null;
  ready: boolean;
  signIn: (email: string, password: string, register?: boolean) => Promise<void>;
  signOut: () => Promise<void>;
  apiFetch: (path: string, init?: RequestInit) => Promise<any>;
};
const Context = createContext<AuthState | null>(null);
let refreshInFlight: Promise<string | null> | null = null;

function refreshAccessToken(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = publicRequest('/api/v1/auth/refresh', { method: 'POST' })
      .then((data: { access_token: string }) => data.access_token)
      .catch(() => null)
      .finally(() => { refreshInFlight = null; });
  }
  return refreshInFlight;
}

async function readError(response: Response): Promise<string> {
  const data = await response.json().catch(() => ({}));
  return data.detail?.message || data.detail || 'Something went wrong. Please try again.';
}

export async function publicRequest(path: string, init: RequestInit = {}) {
  const response = await fetch(`${API}${path}`, { ...init, credentials: 'include',
    headers: { ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...init.headers } });
  if (!response.ok) throw new Error(await readError(response));
  return response.status === 204 ? null : response.json();
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let mounted = true;
    refreshAccessToken().then(async freshToken => {
      if (!mounted) return;
      if (freshToken) {
        setToken(freshToken);
        try {
          const response = await publicRequest('/api/v1/users/me', { headers: { Authorization: `Bearer ${freshToken}` } });
          if (mounted) setUser(response);
        } catch { if (mounted) setToken(null); }
      }
      if (mounted) setReady(true);
    });
    return () => { mounted = false; };
  }, []);

  const signIn = async (email: string, password: string, register = false) => {
    const data = await publicRequest(`/api/v1/auth/${register ? 'register' : 'login'}`, {
      method: 'POST', body: JSON.stringify({ email, password }),
    });
    setToken(data.access_token);
    const profile = await publicRequest('/api/v1/users/me', { headers: { Authorization: `Bearer ${data.access_token}` } });
    setUser(profile);
    setReady(true);
  };

  const signOut = async () => {
    try { await publicRequest('/api/v1/auth/logout', { method: 'POST' }); }
    finally { setToken(null); setUser(null); }
  };

  const apiFetch = async (path: string, init: RequestInit = {}) => {
    const send = (activeToken: string | null) => fetch(`${API}${path}`, { ...init, credentials: 'include',
      headers: { ...(init.body ? { 'Content-Type': 'application/json' } : {}),
        ...(activeToken ? { Authorization: `Bearer ${activeToken}` } : {}), ...init.headers } });
    let response = await send(token);
    if (response.status === 401 && token) {
      const freshToken = await refreshAccessToken();
      if (freshToken) {
        setToken(freshToken);
        response = await send(freshToken);
      } else {
        setToken(null);
        setUser(null);
      }
    }
    if (!response.ok) throw new Error(await readError(response));
    return response.status === 204 ? null : response.json();
  };

  return <Context.Provider value={{ token, user, ready, signIn, signOut, apiFetch }}>{children}</Context.Provider>;
}

export function useAuth() {
  const value = useContext(Context);
  if (!value) throw new Error('useAuth must be used within AuthProvider');
  return value;
}
