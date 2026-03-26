import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Register() {
  const [form, setForm] = useState({
    username: '', email: '', password: '', confirmPassword: '',
    first_name: '', last_name: '', has_diabetes: false, diabetes_type: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const loadingFailsafeRef = useRef(null);
  const { register } = useAuth();
  const navigate = useNavigate();

  useEffect(() => () => clearTimeout(loadingFailsafeRef.current), []);

  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm((f) => ({ ...f, [name]: type === 'checkbox' ? checked : value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    setError('');
    setLoading(true);
    clearTimeout(loadingFailsafeRef.current);
    loadingFailsafeRef.current = setTimeout(() => {
      setLoading(false);
      setError((prev) =>
        prev ||
        'Still waiting on the server. From Meal-Plan-System/backend run: $env:PORT="8001"; python run.py — then open this site’s /api/health (expect glocusense-meal-plan).'
      );
    }, 48_000);
    try {
      await register({
        username: form.username,
        email: form.email,
        password: form.password,
        first_name: form.first_name,
        last_name: form.last_name,
        has_diabetes: form.has_diabetes,
        diabetes_type: form.has_diabetes ? form.diabetes_type : null
      });
      navigate('/app');
    } catch (err) {
      setError(err.message || 'Registration failed');
    } finally {
      clearTimeout(loadingFailsafeRef.current);
      loadingFailsafeRef.current = null;
      setLoading(false);
    }
  }

  const inputClass =
    'w-full rounded-[10px] border border-slate-200 px-4 py-3.5 text-base transition-all focus:border-blue-600 focus:shadow-[0_0_0_3px_rgba(37,99,235,0.1)] focus:outline-none';

  return (
    <div className="auth-page-noise relative flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-600 via-blue-700 to-blue-900 px-5 py-8 font-sans">
      <div className="relative flex w-full max-w-[520px] flex-col items-stretch">
        <Link
          to="/"
          className="mb-6 inline-flex items-center gap-2 text-[0.9375rem] text-white/90 no-underline transition-opacity hover:text-white hover:opacity-100"
        >
          <i className="fas fa-arrow-left" /> Back to home
        </Link>
        <div className="relative w-full rounded-[20px] bg-white p-10 shadow-[0_25px_50px_rgba(0,0,0,0.15)] max-sm:p-7">
          <div className="mb-8 text-center">
            <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-100 to-blue-300 text-[1.75rem] text-blue-700">
              <i className="fas fa-user-plus" />
            </div>
            <h1 className="m-0 mb-1 font-outfit text-[1.75rem] font-bold text-slate-900">Create Account</h1>
            <p className="m-0 text-base text-slate-500">Join Glocusense today</p>
          </div>
          {error && <div className="alert alert-error mb-5 rounded-[10px]">{error}</div>}
          <form onSubmit={handleSubmit}>
            <div className="mb-5">
              <label className="form-label">Username *</label>
              <input
                type="text"
                name="username"
                className={inputClass}
                value={form.username}
                onChange={handleChange}
                placeholder="Choose a username"
                required
                disabled={loading}
              />
            </div>
            <div className="mb-5">
              <label className="form-label">Email *</label>
              <input
                type="email"
                name="email"
                className={inputClass}
                value={form.email}
                onChange={handleChange}
                placeholder="your@email.com"
                required
                disabled={loading}
              />
            </div>
            <div className="mb-5">
              <label className="form-label">Password *</label>
              <input
                type="password"
                name="password"
                className={inputClass}
                value={form.password}
                onChange={handleChange}
                placeholder="Create a password"
                required
                disabled={loading}
              />
            </div>
            <div className="mb-5">
              <label className="form-label">Confirm Password *</label>
              <input
                type="password"
                name="confirmPassword"
                className={inputClass}
                value={form.confirmPassword}
                onChange={handleChange}
                placeholder="Repeat password"
                required
                disabled={loading}
              />
            </div>
            <div className="mb-5">
              <label className="form-label">Full Name (optional)</label>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <input
                  type="text"
                  name="first_name"
                  className={inputClass}
                  placeholder="First name"
                  value={form.first_name}
                  onChange={handleChange}
                  disabled={loading}
                />
                <input
                  type="text"
                  name="last_name"
                  className={inputClass}
                  placeholder="Last name"
                  value={form.last_name}
                  onChange={handleChange}
                  disabled={loading}
                />
              </div>
            </div>
            <div className="mb-5">
              <label className="flex cursor-pointer items-center gap-2 text-[0.9375rem]">
                <input
                  type="checkbox"
                  name="has_diabetes"
                  className="h-[1.125rem] w-[1.125rem] accent-blue-600"
                  checked={form.has_diabetes}
                  onChange={handleChange}
                  disabled={loading}
                />
                I have diabetes
              </label>
              {form.has_diabetes && (
                <div className="mt-4">
                  <label className="form-label">Diabetes Type</label>
                  <select
                    name="diabetes_type"
                    className="form-select rounded-[10px]"
                    value={form.diabetes_type}
                    onChange={handleChange}
                    disabled={loading}
                  >
                    <option value="">Select type...</option>
                    <option value="Type 1">Type 1</option>
                    <option value="Type 2">Type 2</option>
                    <option value="Gestational">Gestational</option>
                    <option value="Prediabetes">Prediabetes</option>
                  </select>
                </div>
              )}
            </div>
            <button
              type="submit"
              className="btn btn-primary btn-full mt-1 rounded-[10px] px-6 py-3.5 text-base"
              disabled={loading}
            >
              {loading ? (
                <>
                  <i className="fas fa-spinner fa-spin" /> Creating Account...
                </>
              ) : (
                <>
                  <i className="fas fa-user-plus" /> Create Account
                </>
              )}
            </button>
          </form>
          <div className="mt-6 border-t border-slate-200 pt-6 text-center">
            <p className="m-0 text-[0.9375rem] text-slate-500">
              Already have an account?{' '}
              <Link to="/login" className="font-semibold text-blue-600 no-underline hover:underline">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
