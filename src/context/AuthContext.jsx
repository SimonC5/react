import { createContext, useContext, useEffect, useState } from 'react';
import { authApi } from '../services/api';

const AuthContext = createContext(null);
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!localStorage.getItem('simonsc_token')) return setLoading(false);
    authApi.me().then(({ user: currentUser }) => setUser(currentUser)).catch(() => localStorage.removeItem('simonsc_token')).finally(() => setLoading(false));
  }, []);
  const login = async (credentials) => { const result = await authApi.login(credentials); localStorage.setItem('simonsc_token', result.token); setUser(result.user); return result.user; };
  const logout = () => { localStorage.removeItem('simonsc_token'); setUser(null); };
  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}
export function useAuth() { return useContext(AuthContext); }
