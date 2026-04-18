import { Link } from 'react-router-dom'
import {
  FiArrowRight,
  FiCheck,
  FiCoffee,
  FiShield,
  FiUsers,
} from 'react-icons/fi'
import { getMealPlanOrigin, getPublicSiteHostname, WORKSPACE_PATH } from '../constants'
import BrandLogo from '../components/BrandLogo'

/**
 * Public landing — unified GlucoSense (clinical CDS) + Glocusense Meal Plan (nutrition).
 */
export default function LandingPage() {
  const mealPlanRegisterUrl = `${getMealPlanOrigin()}/register`

  return (
    <div className="unified-landing">
      <header className="unified-landing-header">
        <div className="unified-landing-brand">
          <div className="unified-landing-logo-wrap unified-landing-logo-wrap--mark" aria-hidden>
            <BrandLogo size={44} />
          </div>
          <div>
            <h1>GlucoSense</h1>
            <p className="unified-landing-public-host">{getPublicSiteHostname()}</p>
            <p>Clinical intelligence & nutrition - one calm workspace</p>
          </div>
        </div>
        <nav className="unified-landing-nav" aria-label="Primary">
          <a href="#features" className="unified-landing-nav-link">
            Features
          </a>
          <a href="#roles" className="unified-landing-nav-link">
            Who this is for
          </a>
          <a href={`${mealPlanRegisterUrl}`} className="unified-landing-nav-link">
            Sign up
          </a>
          <Link to={WORKSPACE_PATH} className="unified-landing-cta">
            Open clinical workspace
          </Link>
        </nav>
      </header>

      <main className="unified-landing-main">
        <section className="unified-landing-hero" aria-labelledby="landing-hero-title">
          <div className="unified-landing-hero-grid">
            <div className="unified-landing-hero-copy">
              <span className="unified-landing-eyebrow">Type 1 diabetes care</span>
              <h2 id="landing-hero-title">
                Smarter insulin support and meal planning - together
              </h2>
              <p className="unified-landing-lead">
                One portal for clinicians who need decision support and for patients who want focused
                nutrition tools. Clear roles, one experience.
              </p>
              <ul className="unified-landing-checklist">
                <li>
                  <FiCheck className="unified-landing-check-icon" aria-hidden />
                  <span>Insulin guidance, explainability, alerts, and reports</span>
                </li>
                <li>
                  <FiCheck className="unified-landing-check-icon" aria-hidden />
                  <span>Integrated meal search, recommendations, and glucose logging</span>
                </li>
                <li>
                  <FiCheck className="unified-landing-check-icon" aria-hidden />
                  <span>Clinical workspace opens directly; Meal Plan nutrition app has its own login when used standalone</span>
                </li>
              </ul>
              <div className="unified-landing-hero-actions">
                <Link to={WORKSPACE_PATH} className="unified-btn unified-btn-primary unified-btn-lg">
                  Open clinical workspace
                  <FiArrowRight className="unified-btn-icon" aria-hidden />
                </Link>
                <a href={mealPlanRegisterUrl} className="unified-btn unified-btn-secondary unified-btn-lg">
                  Create account
                </a>
                <div className="unified-landing-hero-split">
                  <Link to={WORKSPACE_PATH} className="unified-landing-text-link">
                    Clinical workspace
                  </Link>
                  <span className="unified-landing-dot" aria-hidden />
                  <Link to="/meal-plan" className="unified-landing-text-link">
                    Meal planning (iframe)
                  </Link>
                </div>
              </div>
            </div>

            <div className="unified-landing-hero-visual" aria-hidden>
              <div className="unified-landing-glow" />
              <div className="unified-landing-mockup">
                <div className="unified-landing-mockup-header">
                  <span className="unified-landing-mockup-dot" />
                  <span className="unified-landing-mockup-dot" />
                  <span className="unified-landing-mockup-dot" />
                </div>
                <div className="unified-landing-mockup-body">
                  <div className="unified-landing-mockup-line unified-landing-mockup-line--long" />
                  <div className="unified-landing-mockup-line unified-landing-mockup-line--med" />
                  <div className="unified-landing-mockup-cards">
                    <div className="unified-landing-mockup-chip">CDS</div>
                    <div className="unified-landing-mockup-chip unified-landing-mockup-chip--alt">Meals</div>
                  </div>
                  <div className="unified-landing-mockup-line unified-landing-mockup-line--short" />
                </div>
              </div>
            </div>
          </div>
        </section>

        <div className="unified-landing-strip" role="presentation">
          <div className="unified-landing-strip-item">
            <strong>One sign-in</strong>
            <span>Portal + meal module</span>
          </div>
          <div className="unified-landing-strip-divider" aria-hidden />
          <div className="unified-landing-strip-item">
            <strong>Type 1 focus</strong>
            <span>Built for real clinical workflows</span>
          </div>
          <div className="unified-landing-strip-divider" aria-hidden />
          <div className="unified-landing-strip-item">
            <strong>Role-aware</strong>
            <span>Right tools for each user</span>
          </div>
        </div>

        <section id="features" className="unified-landing-section" aria-labelledby="features-title">
          <div className="unified-landing-section-head">
            <h2 id="features-title">What GlucoSense includes</h2>
            <p>Three pillars - clinical depth, everyday nutrition, and access that matches responsibility.</p>
          </div>
          <div className="unified-landing-grid">
            <article className="unified-card unified-card--lift">
              <FiShield className="unified-card-icon" aria-hidden />
              <h3>Clinical CDS</h3>
              <p>
                Insulin recommendations with explainability, patient records, alerts, and reporting - designed
                for licensed clinicians using decision support responsibly.
              </p>
            </article>
            <article className="unified-card unified-card--lift">
              <FiCoffee className="unified-card-icon" aria-hidden />
              <h3>Meal plan &amp; nutrition</h3>
              <p>
                Food search, a nutrition assistant, meal recommendations, and glucose tracking from the integrated
                meal-plan experience - embedded in the same portal.
              </p>
            </article>
            <article className="unified-card unified-card--lift">
              <FiUsers className="unified-card-icon" aria-hidden />
              <h3>Role-based access</h3>
              <p>
                After sign-in, clinicians see the full dashboard plus meal tools. Patients go straight to meal
                planning - simple, focused self-management.
              </p>
            </article>
          </div>
        </section>

        <section id="roles" className="unified-landing-section unified-landing-section--alt" aria-labelledby="roles-title">
          <div className="unified-landing-section-head">
            <h2 id="roles-title">Choose your path</h2>
            <p>Same platform - tailored entry points after you sign in.</p>
          </div>
          <div className="unified-landing-roles">
            <article className="unified-landing-role-card">
              <div className="unified-landing-role-icon" aria-hidden>
                <FiShield />
              </div>
              <h3>Clinician</h3>
              <p>Workspace, patients, insulin support, reports, alerts - and meal planning when you need it.</p>
              <Link to={WORKSPACE_PATH} className="unified-landing-role-cta">
                Open clinical workspace <FiArrowRight size={16} aria-hidden />
              </Link>
            </article>
            <article className="unified-landing-role-card unified-landing-role-card--patient">
              <div className="unified-landing-role-icon unified-landing-role-icon--patient" aria-hidden>
                <FiCoffee />
              </div>
              <h3>Patient</h3>
              <p>Meal planning, food discovery, and glucose tools - without the clinical dashboard.</p>
              <Link to="/meal-plan" className="unified-landing-role-cta">
                Open meal planning <FiArrowRight size={16} aria-hidden />
              </Link>
            </article>
          </div>
        </section>

        <section className="unified-landing-cta-band" aria-labelledby="cta-band-title">
          <div className="unified-landing-cta-inner">
            <h2 id="cta-band-title">Accounts &amp; demos</h2>
            <p className="unified-landing-cta-lead">
              <strong>GlucoSense clinical</strong> opens without login. <strong>Meal Plan</strong> (nutrition app)
              uses its own account when you use it standalone or register for meals.
            </p>

            <div className="unified-landing-signin" role="region" aria-label="Demo accounts">
              <p>
                <strong>Meal Plan only:</strong>{' '}
                <a href={mealPlanRegisterUrl} className="unified-landing-inline-link">
                  register
                </a>{' '}
                or sign in on the Meal Plan app — not required for GlucoSense clinical tools.
              </p>
              <p>
                <strong>Optional dev seed</strong> (run once from Meal Plan backend:{' '}
                <code className="unified-landing-code">python scripts/seed_test_user.py</code>):
              </p>
              <ul className="unified-landing-demo-list">
                <li>
                  Patient — <code>zoe@test.com</code> or username <code>Zoe</code> / <code>Zoe123</code>
                </li>
                <li>
                  Clinician workspace — <code>clinician@demo.local</code> or <code>ClinicianDemo</code> /{' '}
                  <code>DemoClinician123</code>
                </li>
              </ul>
            </div>

            <p className="unified-landing-cta-more">
              Prefer to start in the Meal Plan app?{' '}
              <a href={`${getMealPlanOrigin()}/login`} className="unified-landing-inline-link">
                Open Meal Plan sign-in
              </a>{' '}
              or{' '}
              <a href={mealPlanRegisterUrl} className="unified-landing-inline-link">
                Create account
              </a>
              .
            </p>

            <div className="unified-landing-cta-band-actions">
              <Link to={WORKSPACE_PATH} className="unified-btn unified-btn-on-dark unified-btn-lg">
                Open clinical workspace
                <FiArrowRight className="unified-btn-icon" aria-hidden />
              </Link>
              <Link to="/login" className="unified-btn unified-btn-secondary unified-btn-on-dark unified-btn-lg">
                Link Meal Plan (optional SSO)
              </Link>
              <a href={mealPlanRegisterUrl} className="unified-btn unified-btn-secondary unified-btn-on-dark unified-btn-lg">
                Sign up (Meal Plan)
              </a>
            </div>
          </div>
        </section>

        <p className="unified-landing-disclaimer">
          <strong>Clinical safety:</strong> GlucoSense supports - but does not replace - professional medical
          judgment. Meal Plan information is for education and self-management; confirm any care changes with your
          health team.
        </p>
      </main>

      <footer className="unified-landing-footer">
        <span className="unified-landing-footer-brand">
          <BrandLogo size={20} /> GlucoSense
        </span>
        <span className="unified-landing-footer-meta">Clinical decision support &amp; nutrition</span>
      </footer>
    </div>
  )
}
