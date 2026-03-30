import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';

const AuthContext = createContext(null);

function getInitialEmbedHandoffPending() {
  try {
    if (typeof window === 'undefined') return false;
    const embed = new URLSearchParams(window.location.search).get('embed') === 'glucosense';
    if (!embed) return false;
    return !localStorage.getItem('token');
  } catch {
    return false;
  }
}

/** Parent window (GlucoSense) may be opened as http://192.168.x.x:5173 on a LAN — not only localhost. */
function isPrivateLanHttpOrigin(origin) {
  try {
    const u = new URL(origin);
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return false;
    const h = u.hostname;
    if (h === 'localhost' || h === '127.0.0.1' || h === '[::1]') return true;
    if (/^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(h)) return true;
    if (/^192\.168\.\d{1,3}\.\d{1,3}$/.test(h)) return true;
    return /^172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}$/.test(h);
  } catch {
    return false;
  }
}

function isAllowedGlucosenseOrigin(origin) {
  const o = origin || '';
  if (/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(o)) return true;
  if (/^https?:\/\/\[::1\](:\d+)?$/i.test(o)) return true;
  if (isPrivateLanHttpOrigin(o)) return true;
  const extra = import.meta.env.VITE_ALLOWED_GLUCOSENSE_ORIGINS;
  if (typeof extra !== 'string' || !extra.trim()) return false;
  return extra.split(',').some((item) => {
    const e = item.trim();
    return e.length > 0 && o === e;
  });
}

/** Only show global “session restore” loading when a token exists; avoids a one-frame flash on /app for logged-out users. */
function getInitialAuthLoading() {
  if (typeof window === 'undefined') return true;
  return !!localStorage.getItem('token');
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(getInitialAuthLoading);
  const [embedHandoffPending, setEmbedHandoffPending] = useState(getInitialEmbedHandoffPending);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const embedGlucosense =
      typeof window !== 'undefined' &&
      new URLSearchParams(window.location.search).get('embed') === 'glucosense';
    if (!token) {
      setLoading(false);
      return;
    }
    // Failsafe: never leave global `loading` true forever if /me hangs (dead API / wrong port).
    const failsafe = setTimeout(() => setLoading(false), 48_000);
    api.auth
      .me()
      .then((data) => {
        if (data?.user) setUser(data.user);
        else {
          localStorage.removeItem('token');
          if (embedGlucosense) setEmbedHandoffPending(true);
        }
      })
      .catch(() => {
        localStorage.removeItem('token');
        // Stale standalone token in iframe: wait for GlucoSense parent to post a fresh JWT.
        if (embedGlucosense) setEmbedHandoffPending(true);
      })
      .finally(() => {
        clearTimeout(failsafe);
        setLoading(false);
      });
  }, []);

  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      setUser(null);
      return null;
    }
    try {
      const data = await api.auth.me();
      if (data?.user) {
        setUser(data.user);
        return data.user;
      }
      localStorage.removeItem('token');
      setUser(null);
      return null;
    } catch {
      localStorage.removeItem('token');
      setUser(null);
      return null;
    }
  }, []);

  /** Token pushed from GlucoSense parent window (iframe embed). */
  useEffect(() => {
    const embedQs = () =>
      typeof window !== 'undefined' &&
      new URLSearchParams(window.location.search).get('embed') === 'glucosense';

    const onMessage = (event) => {
      if (!isAllowedGlucosenseOrigin(event.origin)) return;
      const { type, token } = event.data || {};
      if (type === 'GLUCOSENSE_MEAL_PLAN_TOKEN' && typeof token === 'string' && token.length > 0) {
        localStorage.setItem('token', token);
        setEmbedHandoffPending(false);
        setLoading(true);
        api.auth
          .me()
          .then((data) => {
            if (data?.user) setUser(data.user);
            else {
              localStorage.removeItem('token');
              if (embedQs()) setEmbedHandoffPending(true);
            }
          })
          .catch(() => {
            localStorage.removeItem('token');
            if (embedQs()) setEmbedHandoffPending(true);
          })
          .finally(() => setLoading(false));
      }
      if (type === 'GLUCOSENSE_MEAL_PLAN_LOGOUT') {
        localStorage.removeItem('token');
        setUser(null);
        setEmbedHandoffPending(false);
        setLoading(false);
      }
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, []);

  const login = async (username, password) => {
    const res = await api.auth.login(username, password);
    if (!res?.token || !res?.user) {
      throw new Error('Invalid login response from server');
    }
    localStorage.setItem('token', res.token);
    setUser(res.user);
    return res.user;
  };

  const register = async (data) => {
    const res = await api.auth.register(data);
    if (!res?.token || !res?.user) {
      throw new Error('Invalid registration response from server');
    }
    localStorage.setItem('token', res.token);
    setUser(res.user);
    return res.user;
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, logout, refreshUser, embedHandoffPending }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
