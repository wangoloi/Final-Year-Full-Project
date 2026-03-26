import React, { useMemo, useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const MEAL_SLOTS = [
  { key: 'breakfast', label: 'Breakfast', icon: 'fa-mug-hot' },
  { key: 'lunch', label: 'Lunch', icon: 'fa-bowl-food' },
  { key: 'dinner', label: 'Dinner', icon: 'fa-utensils' },
  { key: 'snack', label: 'Snack', icon: 'fa-apple-whole' },
];

function buildWeeklyPlan(foods) {
  if (!foods?.length) {
    return DAYS.map((day) => ({
      day,
      meals: MEAL_SLOTS.map((s) => ({ ...s, food: null })),
    }));
  }
  const totalSlots = DAYS.length * MEAL_SLOTS.length;
  const picks = [];
  for (let i = 0; i < totalSlots; i += 1) {
    picks.push(foods[i % foods.length]);
  }
  let i = 0;
  return DAYS.map((day) => ({
    day,
    meals: MEAL_SLOTS.map((slot) => ({
      ...slot,
      food: picks[i++],
    })),
  }));
}

function MealTile({ food, label, iconClass }) {
  const slotStyles =
    'mb-3 flex items-center gap-2 border-b border-slate-200/80 pb-2 text-[0.6875rem] font-bold uppercase tracking-[0.14em] text-blue-700';

  if (!food) {
    return (
      <div className="flex min-h-[7.75rem] flex-col rounded-xl border border-dashed border-slate-200 bg-slate-50/90 p-4">
        <div className={slotStyles}>
          <i className={`fas ${iconClass} text-[0.8125rem] text-blue-600`} aria-hidden />
          {label}
        </div>
        <p className="mb-0 mt-auto text-sm leading-relaxed text-slate-400">Add foods from recommendations</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-[7.75rem] flex-col rounded-xl border border-slate-100 bg-slate-50 p-4 shadow-sm ring-1 ring-slate-100/80 transition-all duration-200 hover:border-blue-100 hover:shadow-md hover:ring-blue-100/50">
      <div className={slotStyles}>
        <i className={`fas ${iconClass} text-[0.8125rem] text-blue-600`} aria-hidden />
        {label}
      </div>
      <h4 className="mb-2 line-clamp-2 text-[0.9375rem] font-semibold leading-snug text-slate-900 sm:text-base">
        {food.name}
      </h4>
      <div className="mt-auto space-y-1">
        <p className="mb-0 text-[0.8125rem] leading-relaxed text-slate-600">
          <span className="font-medium text-slate-700">{food.calories}</span>
          <span className="text-slate-400"> cal</span>
          <span className="text-slate-300"> · </span>
          <span className="text-slate-600">GI </span>
          <span className="font-medium text-slate-800">{food.glycemic_index ?? '—'}</span>
        </p>
        <p
          className="mb-0 truncate text-[0.8125rem] leading-normal text-slate-500"
          title={food.category}
        >
          {food.category}
        </p>
      </div>
    </div>
  );
}

export default function MealPlan() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api
      .recommendations(28)
      .then((data) => setItems(data.recommendations || []))
      .catch((err) => setError(err.message || 'Failed to load meal ideas'))
      .finally(() => setLoading(false));
  }, []);

  const week = useMemo(() => buildWeeklyPlan(items), [items]);

  return (
    <div className="page-content mx-auto w-full max-w-6xl gap-10 pb-2 sm:gap-12">
      {/* Hero */}
      <header className="page-header overflow-hidden rounded-2xl px-5 py-6 shadow-header-chat sm:px-8 sm:py-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between lg:gap-8">
          <div className="flex min-w-0 flex-1 items-start gap-4 sm:gap-5">
            <div
              className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-white/15 text-white shadow-inner sm:h-16 sm:w-16 sm:text-[1.75rem]"
              aria-hidden
            >
              <i className="fas fa-calendar-week" />
            </div>
            <div className="min-w-0 pt-0.5">
              <p className="mb-3 inline-flex items-center rounded-full bg-white/20 px-3.5 py-1.5 text-[0.6875rem] font-semibold uppercase tracking-[0.12em] text-white/95">
                Low-GI · Balanced week
              </p>
              <h1 className="!mb-2 font-sans text-3xl font-bold tracking-tight text-white sm:text-4xl">
                Your meal plan
              </h1>
              <p className="m-0 max-w-xl text-sm leading-relaxed text-white/90 sm:text-base">
                Seven days, four meals each—pulled from your recommendations and styled like your dashboard cards for
                quick scanning.
              </p>
            </div>
          </div>
          <div className="flex w-full flex-col gap-2 sm:flex-row sm:flex-wrap lg:w-auto lg:min-w-[11rem] lg:flex-col lg:gap-2.5">
            <Link
              to="/app/recommendations"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-semibold text-blue-700 shadow-sm transition-colors hover:bg-blue-50"
            >
              <i className="fas fa-seedling text-base" aria-hidden />
              Refresh ideas
            </Link>
            <Link
              to="/app/search"
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/45 bg-white/5 px-5 py-3 text-sm font-medium text-white backdrop-blur-[2px] transition-colors hover:bg-white/15"
            >
              <i className="fas fa-search" aria-hidden />
              Search foods
            </Link>
          </div>
        </div>
      </header>

      {error && (
        <div className="alert alert-error rounded-xl text-sm sm:text-[0.9375rem]">
          {error}
        </div>
      )}

      {loading ? (
        <div className="rounded-2xl border border-slate-200/90 bg-white px-6 py-16 text-center shadow-sm sm:px-8 sm:py-20">
          <div className="spinner-border text-primary mx-auto" role="status" aria-label="Loading" />
          <p className="mt-4 mb-0 text-sm text-slate-600 sm:text-base">Building your week from recommendations…</p>
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-2xl border border-slate-200/90 bg-white px-6 py-12 text-center shadow-sm sm:px-10 sm:py-14">
          <div className="mx-auto mb-5 flex h-[4.5rem] w-[4.5rem] items-center justify-center rounded-2xl bg-blue-50 text-2xl text-blue-600">
            <i className="fas fa-utensils" aria-hidden />
          </div>
          <h2 className="mb-2 text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl">No recommendations yet</h2>
          <p className="mx-auto mb-8 max-w-md text-sm leading-relaxed text-slate-600 sm:text-base">
            Complete your profile or open recommendations so we can fill this plan with foods that match your goals.
          </p>
          <Link to="/app/recommendations" className="btn btn-primary px-6 py-3 text-sm sm:text-[0.9375rem]">
            <i className="fas fa-seedling" /> Go to recommendations
          </Link>
        </div>
      ) : (
        <section
          className="rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm sm:p-8 md:p-9"
          aria-labelledby="meal-plan-week"
        >
          <div className="mb-8 flex flex-col gap-4 border-b border-slate-100 pb-6 sm:mb-10 sm:flex-row sm:items-end sm:justify-between sm:gap-6 sm:pb-8">
            <div className="min-w-0">
              <h2
                id="meal-plan-week"
                className="mb-0 flex flex-wrap items-center gap-3 text-lg font-semibold tracking-tight text-blue-700 sm:text-xl"
              >
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600 sm:h-12 sm:w-12">
                  <i className="fas fa-clipboard-list text-lg" aria-hidden />
                </span>
                <span>This week at a glance</span>
              </h2>
            </div>
            <p className="mb-0 max-w-prose text-xs leading-relaxed text-slate-500 sm:max-w-sm sm:text-right sm:text-sm">
              <span className="font-medium text-slate-600">{items.length} foods</span> cycled across{' '}
              <span className="font-medium text-slate-600">{DAYS.length} days</span>. Swap items anytime—confirm changes
              with your care team.
            </p>
          </div>

          <div className="flex flex-col gap-10 sm:gap-12">
            {week.map(({ day, meals }) => (
              <div key={day} className="scroll-mt-4">
                <h3 className="mb-4 flex items-center gap-3 sm:mb-5">
                  <span className="h-1 w-10 shrink-0 rounded-full bg-blue-600" aria-hidden />
                  <span className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500 sm:text-[0.8125rem]">
                    {day}
                  </span>
                </h3>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 lg:gap-5">
                  {meals.map(({ label, icon, food }) => (
                    <MealTile key={`${day}-${label}`} food={food} label={label} iconClass={icon} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Tips */}
      <section className="grid grid-cols-1 gap-5 md:grid-cols-3 md:gap-6" aria-labelledby="meal-plan-tips">
        <h2 id="meal-plan-tips" className="sr-only">
          Meal planning tips
        </h2>
        <article className="flex flex-col rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm transition-shadow duration-200 hover:shadow-md sm:p-7">
          <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-100 to-blue-200 text-lg text-blue-800">
            <i className="fas fa-scale-balanced" aria-hidden />
          </div>
          <h3 className="mb-2 font-outfit text-base font-semibold text-slate-900 sm:text-lg">Balance each meal</h3>
          <p className="mb-0 text-sm leading-relaxed text-slate-600">
            Pair carbs with protein and fiber—the same idea as your recommendation cards—to support steadier glucose
            after meals.
          </p>
        </article>
        <article className="flex flex-col rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm transition-shadow duration-200 hover:shadow-md sm:p-7">
          <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-100 to-blue-200 text-lg text-blue-800">
            <i className="fas fa-ruler-combined" aria-hidden />
          </div>
          <h3 className="mb-2 font-outfit text-base font-semibold text-slate-900 sm:text-lg">Watch portions</h3>
          <p className="mb-0 text-sm leading-relaxed text-slate-600">
            Calories and GI are guides only. Your clinician sets portion sizes that fit your targets and medications.
          </p>
        </article>
        <article className="flex flex-col rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm transition-shadow duration-200 hover:shadow-md sm:p-7">
          <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-100 to-blue-200 text-lg text-blue-800">
            <i className="fas fa-droplet" aria-hidden />
          </div>
          <h3 className="mb-2 font-outfit text-base font-semibold text-slate-900 sm:text-lg">Hydrate &amp; adjust</h3>
          <p className="mb-0 text-sm leading-relaxed text-slate-600">
            Drink water with meals, notice how you feel, and fine-tune with your team—not every day needs the same menu.
          </p>
        </article>
      </section>

      <p className="mx-auto mb-0 max-w-2xl px-2 text-center text-[0.8125rem] leading-relaxed text-slate-500">
        This plan is educational and built from app suggestions only.{' '}
        <span className="font-semibold text-slate-600">Not medical advice</span>
        —follow your registered dietitian or clinician.
      </p>
    </div>
  );
}
