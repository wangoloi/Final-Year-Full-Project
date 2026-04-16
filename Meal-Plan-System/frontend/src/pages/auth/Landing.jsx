import React from 'react';
import { Link } from 'react-router-dom';
import Heading from '../../ui/Heading';
import Text from '../../ui/Text';
import Button from '../../ui/Button';

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
            <Button
              as={Link}
              to="/login"
              variant="ghostOnDark"
              size="sm"
              className="border-white/40 hover:border-white/60"
            >
              Login
            </Button>
            <Button
              as={Link}
              to="/register"
              variant="secondary"
              size="sm"
              className="bg-white text-blue-700 hover:bg-blue-50 hover:text-blue-600"
            >
              Get Started
            </Button>
          </div>
        </nav>

        <div className="relative z-[2] container mx-auto max-w-[680px] text-center">
          <span className="mb-5 inline-block rounded-full bg-white/20 px-3 py-1.5 text-caption font-medium tracking-wide text-white">
            Diabetes-Friendly Nutrition
          </span>
          <Heading
            level={1}
            tone="onDark"
            className="mb-4 text-[clamp(2.125rem,5vw,3rem)] leading-tight"
          >
            Meal planning that <em className="not-italic text-blue-300">cares</em> for your health
          </Heading>
          <Text as="p" tone="onDark" className="mb-8 text-[clamp(1rem,2.5vw,1.125rem)]">
            Find low-glycemic foods, track blood glucose, and get personalized meal recommendations.
            Designed for people managing diabetes—simple, practical, and supportive.
          </Text>
          <div className="flex flex-wrap justify-center gap-4 max-sm:flex-col">
            <Button
              as={Link}
              to="/register"
              variant="secondary"
              className="px-6 py-3.5 text-base bg-white text-blue-700 hover:bg-blue-50 hover:text-blue-600 max-sm:w-full"
            >
              Start Planning Meals <i className="fas fa-arrow-right" />
            </Button>
            <Button
              as={Link}
              to="/login"
              variant="ghostOnDark"
              className="border-white/60 px-6 py-3.5 text-base hover:border-white hover:bg-white/10 max-sm:w-full"
            >
              I have an account
            </Button>
          </div>
        </div>
      </header>

      <section className="flex-1 bg-slate-50 py-16">
        <div className="container">
          <div className="mx-auto mb-12 max-w-[560px] text-center">
            <Heading level={2} as="h2" className="mb-2 text-blue-700">
              Everything you need to eat well
            </Heading>
            <Text as="p" tone="muted" className="text-[1.0625rem]">
              Smart tools to simplify diabetes management and keep you on track.
            </Text>
          </div>
          <div className="mx-auto grid max-w-[1100px] grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-[repeat(auto-fit,minmax(260px,1fr))]">
            <article className="min-h-[160px] rounded-2xl border border-slate-200 bg-white p-8 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-100 to-blue-300 text-xl text-blue-700">
                <i className="fas fa-apple-whole" />
              </div>
              <Heading level={3} as="h3" className="mb-2">Smart Food Search</Heading>
              <Text as="p" tone="muted" size="helper">
                Find diabetes-friendly local and healthy foods from our curated database.
              </Text>
            </article>
            <article className="min-h-[160px] rounded-2xl border border-slate-200 bg-white p-8 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-100 to-blue-300 text-xl text-blue-700">
                <i className="fas fa-comments" />
              </div>
              <Heading level={3} as="h3" className="mb-2">Nutrition Assistant</Heading>
              <Text as="p" tone="muted" size="helper">
                RAG-based chatbot: ask about glycemic index, carbs, meal ideas, and blood sugar impact.
              </Text>
            </article>
            <article className="min-h-[160px] rounded-2xl border border-slate-200 bg-white p-8 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-100 to-blue-300 text-xl text-blue-700">
                <i className="fas fa-heart-pulse" />
              </div>
              <Heading level={3} as="h3" className="mb-2">Glucose Tracking</Heading>
              <Text as="p" tone="muted" size="helper">
                Record fasting and post-meal readings to understand your patterns.
              </Text>
            </article>
            <article className="min-h-[160px] rounded-2xl border border-slate-200 bg-white p-8 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-100 to-blue-300 text-xl text-blue-700">
                <i className="fas fa-seedling" />
              </div>
              <Heading level={3} as="h3" className="mb-2">Personalized Recommendations</Heading>
              <Text as="p" tone="muted" size="helper">
                Low-glycemic index foods and meal plans tailored to your profile.
              </Text>
            </article>
          </div>
        </div>
      </section>

      <section className="bg-white py-16">
        <div className="container">
          <div className="mx-auto max-w-[560px] rounded-[20px] bg-gradient-to-br from-blue-600 to-blue-700 px-8 py-12 text-center text-white shadow-[0_20px_40px_rgba(37,99,235,0.25)] max-sm:px-6 max-sm:py-8">
            <Heading level={2} as="h2" tone="onDark" className="mb-2 text-[clamp(1.75rem,3vw,2.125rem)]">
              Ready to take control of your meals?
            </Heading>
            <Text as="p" tone="onDark" className="mb-6">
              Join Glocusense and start building healthier eating habits today.
            </Text>
            <Button
              as={Link}
              to="/register"
              variant="secondary"
              className="bg-white px-6 py-3.5 text-base text-blue-700 hover:bg-blue-50 hover:text-blue-600"
            >
              Create free account <i className="fas fa-arrow-right" />
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
