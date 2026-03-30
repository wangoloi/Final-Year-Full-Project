import React from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function Layout() {
  const { logout } = useAuth();

  return (
    <div className="flex min-h-screen w-full flex-col">
      <nav className="bg-gradient-to-br from-blue-600 to-blue-700 py-3 text-white shadow-card-md">
        <div className="mx-auto flex w-full max-w-[1200px] items-center justify-between px-4 lg:px-8">
          <NavLink to="/app" className="flex items-center gap-2 text-white no-underline transition-opacity hover:opacity-95">
            <i className="fas fa-leaf text-2xl" />
            <span className="text-lg font-bold tracking-tight lg:text-xl">Glocusense</span>
          </NavLink>
          <div className="flex flex-wrap items-center gap-1">
            <NavLink
              to="/app"
              className={({ isActive }) =>
                `flex items-center gap-2 rounded px-3.5 py-2 text-sm font-semibold text-white no-underline transition-colors hover:bg-white/20 ${isActive ? 'bg-white/20' : ''}`
              }
              end
            >
              <i className="fas fa-home" />
              <span className="max-md:hidden">Home</span>
            </NavLink>
            <NavLink
              to="/app/meal-plan"
              className={({ isActive }) =>
                `flex items-center gap-2 rounded px-3.5 py-2 text-sm font-semibold text-white no-underline transition-colors hover:bg-white/20 ${isActive ? 'bg-white/20' : ''}`
              }
            >
              <i className="fas fa-utensils" />
              <span className="max-md:hidden">Meals</span>
            </NavLink>
            <NavLink
              to="/app/chatbot"
              className={({ isActive }) =>
                `flex items-center gap-2 rounded px-3.5 py-2 text-sm font-semibold text-white no-underline transition-colors hover:bg-white/20 ${isActive ? 'bg-white/20' : ''}`
              }
            >
              <i className="fas fa-comments" />
              <span className="max-md:hidden">Nutrition</span>
            </NavLink>
            <NavLink
              to="/app/glucose"
              className={({ isActive }) =>
                `flex items-center gap-2 rounded px-3.5 py-2 text-sm font-semibold text-white no-underline transition-colors hover:bg-white/20 ${isActive ? 'bg-white/20' : ''}`
              }
            >
              <i className="fas fa-heart-pulse" />
              <span className="max-md:hidden">Glucose</span>
            </NavLink>
            <button
              type="button"
              className="ml-3 flex cursor-pointer items-center gap-2 rounded border-none bg-transparent px-3.5 py-2 text-sm font-semibold text-white transition-colors hover:bg-white/20"
              onClick={logout}
            >
              <i className="fas fa-sign-out-alt" />
              <span className="max-md:hidden">Logout</span>
            </button>
          </div>
        </div>
      </nav>
      <main className="flex min-h-0 flex-1 flex-col bg-gray-100 py-6">
        <div className="container flex min-h-0 flex-1 flex-col">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
