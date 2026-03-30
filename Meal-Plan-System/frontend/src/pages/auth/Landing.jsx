import React from 'react';
import { Link } from 'react-router-dom';

export default function Landing() {
  return (
    <div className="flex min-h-screen w-full flex-col font-sans">
      <header className="relative overflow-hidden pb-20 pt-6 md:pb-24">
        <div className="absolute inset-0 z-0 bg-gradient-to-br from-blue-600 via-blue-700 to-blue-800" aria-hidden="true" />
        <div
          className="absolute inset-0 z-0 opacity-[0.04]"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E")`,
          }}
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute bottom-0 left-0 right-0 z-[1] h-20 bg-gradient-to-t from-slate-50 to-transparent"
          aria-hidden="true"
        />

        <nav className="relative z-[2] container mb-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 font-outfit text-2xl font-bold tracking-tight text-white no-underline transition-opacity hover:opacity-95">
            <span className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-white/20 text-lg">
              <i className="fas fa-leaf" />
            </span>
            Glocusense
          </Link>
          <div className="flex items-center gap-3">
            <Link
              to="/login"
              className="inline-flex items-center gap-2 rounded-lg border border-white/40 bg-transparent px-4 py-2.5 text-sm font-medium text-white no-underline transition-colors hover:border-white/60 hover:bg-white/10"
            >
              Login
            </Link>
            <Link
              to="/register"
              className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-blue-700 no-underline shadow-sm transition-colors hover:bg-blue-50 hover:text-blue-600"
            >
              Get Started
            </Link>
          </div>
        </nav>

        <div className="relative z-[2] container mx-auto max-w-[680px] text-center">
          <span className="mb-5 inline-block rounded-full bg-white/20 px-3 py-1.5 text-[0.8125rem] font-medium tracking-wide text-white">
            Diabetes-Friendly Nutrition
          </span>
          <h1 className="m-0 mb-4 font-outfit text-[clamp(2rem,5vw,3rem)] font-bold leading-tight tracking-tight text-white">
            Meal planning that <em className="not-italic text-blue-300">cares</em> for your health
          </h1>
          <p className="m-0 mb-8 text-[clamp(1rem,2.5vw,1.125rem)] font-normal leading-relaxed text-white">
            Find low-glycemic foods, track blood glucose, and get personalized meal recommendations.
            Designed for people managing diabetes—simple, practical, and supportive.
          </p>
          <div className="flex flex-wrap justify-center gap-4 max-sm:flex-col">
            <Link
              to="/register"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-6 py-3.5 text-base font-semibold text-blue-700 no-underline shadow-sm transition-colors hover:bg-blue-50 hover:text-blue-600 max-sm:w-full"
            >
              Start Planning Meals <i className="fas fa-arrow-right" />
            </Link>
            <Link
              to="/login"
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/60 bg-transparent px-6 py-3.5 text-base font-medium text-white no-underline transition-colors hover:border-white hover:bg-white/10 max-sm:w-full"
            >
              I have an account
            </Link>
          </div>
        </div>
      </header>

      <section className="flex-1 bg-slate-50 py-16">
        <div className="container">
          <div className="mx-auto mb-12 max-w-[560px] text-center">
            <h2 className="m-0 mb-2 font-outfit text-[clamp(1.75rem,4vw,2.25rem)] font-bold text-blue-700">
              Everything you need to eat well
            </h2>
            <p className="m-0 text-[1.0625rem] text-slate-700">
              Smart tools to simplify diabetes management and keep you on track.
            </p>
          </div>
          <div className="mx-auto grid max-w-[1100px] grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-[repeat(auto-fit,minmax(260px,1fr))]">
            <article className="min-h-[160px] rounded-2xl border border-slate-200 bg-white p-8 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-100 to-blue-300 text-xl text-blue-700">
                <i className="fas fa-apple-whole" />
              </div>
              <h3 className="m-0 mb-2 font-outfit text-lg font-semibold text-slate-900">Smart Food Search</h3>
              <p className="m-0 text-[0.9375rem] leading-relaxed text-slate-700">
                Find diabetes-friendly local and healthy foods from our curated database.
              </p>
            </article>
            <article className="min-h-[160px] rounded-2xl border border-slate-200 bg-white p-8 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-100 to-blue-300 text-xl text-blue-700">
                <i className="fas fa-comments" />
              </div>
              <h3 className="m-0 mb-2 font-outfit text-lg font-semibold text-slate-900">Nutrition Assistant</h3>
              <p className="m-0 text-[0.9375rem] leading-relaxed text-slate-700">
                RAG-based chatbot: ask about glycemic index, carbs, meal ideas, and blood sugar impact.
              </p>
            </article>
            <article className="min-h-[160px] rounded-2xl border border-slate-200 bg-white p-8 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-100 to-blue-300 text-xl text-blue-700">
                <i className="fas fa-heart-pulse" />
              </div>
              <h3 className="m-0 mb-2 font-outfit text-lg font-semibold text-slate-900">Glucose Tracking</h3>
              <p className="m-0 text-[0.9375rem] leading-relaxed text-slate-700">
                Record fasting and post-meal readings to understand your patterns.
              </p>
            </article>
            <article className="min-h-[160px] rounded-2xl border border-slate-200 bg-white p-8 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-100 to-blue-300 text-xl text-blue-700">
                <i className="fas fa-seedling" />
              </div>
              <h3 className="m-0 mb-2 font-outfit text-lg font-semibold text-slate-900">Personalized Recommendations</h3>
              <p className="m-0 text-[0.9375rem] leading-relaxed text-slate-700">
                Low-glycemic index foods and meal plans tailored to your profile.
              </p>
            </article>
          </div>
        </div>
      </section>

      <section className="bg-white py-16">
        <div className="container">
          <div className="mx-auto max-w-[560px] rounded-[20px] bg-gradient-to-br from-blue-600 to-blue-700 px-8 py-12 text-center text-white shadow-[0_20px_40px_rgba(37,99,235,0.25)] max-sm:px-6 max-sm:py-8">
            <h2 className="m-0 mb-2 font-outfit text-[clamp(1.5rem,3vw,1.875rem)] font-bold">
              Ready to take control of your meals?
            </h2>
            <p className="m-0 mb-6 text-base font-normal text-white">
              Join Glocusense and start building healthier eating habits today.
            </p>
            <Link
              to="/register"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-6 py-3.5 text-base font-semibold text-blue-700 no-underline shadow-sm transition-colors hover:bg-blue-50 hover:text-blue-600"
            >
              Create free account <i className="fas fa-arrow-right" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
