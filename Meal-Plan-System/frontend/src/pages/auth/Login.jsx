import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (user) {
      navigate(`/app${location.search || ''}`, { replace: true });
    }
  }, [user, navigate, location.search]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      navigate(`/app${location.search || ''}`);
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page-noise relative flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-600 via-blue-700 to-blue-900 px-5 py-8 font-sans">
      <div className="relative flex w-full max-w-[520px] flex-col items-stretch">
        <Link
          to="/"
          className="mb-6 inline-flex items-center gap-2 text-[0.9375rem] font-medium text-white no-underline transition-opacity hover:opacity-95"
        >
          <i className="fas fa-arrow-left" /> Back to home
        </Link>
        <div className="relative w-full rounded-[20px] bg-white p-10 shadow-[0_25px_50px_rgba(0,0,0,0.15)] max-sm:p-7">
          <div className="mb-8 text-center">
            <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-100 to-blue-300 text-[1.75rem] text-blue-700">
              <i className="fas fa-sign-in-alt" />
            </div>
            <h1 className="m-0 mb-1 font-outfit text-[1.75rem] font-bold text-slate-900">Welcome Back</h1>
            <p className="m-0 text-base text-slate-700">Sign in to your account</p>
          </div>
          {error && <div className="alert alert-error mb-5 rounded-[10px]">{error}</div>}
          <form onSubmit={handleSubmit}>
            <div className="mb-5">
              <label className="mb-2 block text-[0.9375rem] font-semibold text-slate-800">Username or Email</label>
              <input
                type="text"
                className="w-full rounded-[10px] border border-slate-300 bg-white px-4 py-3.5 text-base text-slate-900 placeholder:text-slate-500 transition-all focus:border-blue-600 focus:shadow-[0_0_0_3px_rgba(37,99,235,0.1)] focus:outline-none"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username or email"
                required
                disabled={loading}
              />
            </div>
            <div className="mb-5">
              <label className="mb-2 block text-[0.9375rem] font-semibold text-slate-800">Password</label>
              <input
                type="password"
                className="w-full rounded-[10px] border border-slate-300 bg-white px-4 py-3.5 text-base text-slate-900 placeholder:text-slate-500 transition-all focus:border-blue-600 focus:shadow-[0_0_0_3px_rgba(37,99,235,0.1)] focus:outline-none"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                required
                disabled={loading}
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary btn-full mt-1 rounded-[10px] px-6 py-3.5 text-base"
              disabled={loading}
            >
              {loading ? (
                <>
                  <i className="fas fa-spinner fa-spin" /> Signing In...
                </>
              ) : (
                <>
                  <i className="fas fa-sign-in-alt" /> Sign In
                </>
              )}
            </button>
          </form>
          <div className="mt-6 border-t border-slate-200 pt-6 text-center">
            <p className="m-0 text-[0.9375rem] text-slate-700">
              Don&apos;t have an account?{' '}
              <Link to="/register" className="font-semibold text-blue-600 no-underline hover:underline">
                Sign up
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
