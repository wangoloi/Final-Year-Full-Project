import { Link } from 'react-router-dom'
import {
  FiActivity,
  FiArrowRight,
  FiCheck,
  FiCoffee,
  FiShield,
  FiUsers,
} from 'react-icons/fi'
import Heading from '../ui/Heading'
import Text from '../ui/Text'
import Button from '../ui/Button'

/**
 * Public landing — unified GlucoSense (clinical CDS) + Glocusense Meal Plan (nutrition).
 */
export default function LandingPage() {
  return (
    <div className="unified-landing">
      <header className="unified-landing-header">
        <div className="unified-landing-brand">
          <div className="unified-landing-logo-wrap" aria-hidden>
            <FiActivity className="unified-landing-logo" />
          </div>
          <div>
            <Heading level={1}>GlucoSense</Heading>
            <Text as="p" tone="muted">Clinical intelligence & nutrition - one calm workspace</Text>
          </div>
        </div>
        <nav className="unified-landing-nav" aria-label="Primary">
          <a href="#features" className="unified-landing-nav-link">
            Features
          </a>
          <a href="#roles" className="unified-landing-nav-link">
            Who this is for
          </a>
          <Button as={Link} to="/login" className="unified-landing-cta">
            Sign in
          </Button>
        </nav>
      </header>

      <main className="unified-landing-main">
        <section className="unified-landing-hero" aria-labelledby="landing-hero-title">
          <div className="unified-landing-hero-grid">
            <div className="unified-landing-hero-copy">
              <span className="unified-landing-eyebrow">Type 1 diabetes care</span>
              <Heading level={2} id="landing-hero-title" as="h2">
                Smarter insulin support and meal planning - together
              </Heading>
              <Text className="unified-landing-lead">
                One portal for clinicians who need decision support and for patients who want focused
                nutrition tools. Clear roles, one experience.
              </Text>
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
                  <span>Patients land on meal planning; clinicians unlock the full workspace</span>
                </li>
              </ul>
              <div className="unified-landing-hero-actions">
                <Button as={Link} to="/login" className="unified-btn unified-btn-primary unified-btn-lg">
                  Get started
                  <FiArrowRight className="unified-btn-icon" aria-hidden />
                </Button>
                <div className="unified-landing-hero-split">
                  <Link to="/login?role=clinician" className="unified-landing-text-link">
                    Clinician access
                  </Link>
                  <span className="unified-landing-dot" aria-hidden />
                  <Link to="/login?role=patient" className="unified-landing-text-link">
                    Patient access
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
            <Heading level={2} id="features-title" as="h2">What GlucoSense includes</Heading>
            <Text tone="muted">Three pillars - clinical depth, everyday nutrition, and access that matches responsibility.</Text>
          </div>
          <div className="unified-landing-grid">
            <article className="unified-card unified-card--lift">
              <FiShield className="unified-card-icon" aria-hidden />
              <Heading level={3} as="h3">Clinical CDS</Heading>
              <Text as="p" tone="muted">
                Insulin recommendations with explainability, patient records, alerts, and reporting - designed
                for licensed clinicians using decision support responsibly.
              </Text>
            </article>
            <article className="unified-card unified-card--lift">
              <FiCoffee className="unified-card-icon" aria-hidden />
              <Heading level={3} as="h3">Meal plan &amp; nutrition</Heading>
              <Text as="p" tone="muted">
                Food search, a nutrition assistant, meal recommendations, and glucose tracking from the integrated
                meal-plan experience - embedded in the same portal.
              </Text>
            </article>
            <article className="unified-card unified-card--lift">
              <FiUsers className="unified-card-icon" aria-hidden />
              <Heading level={3} as="h3">Role-based access</Heading>
              <Text as="p" tone="muted">
                After sign-in, clinicians see the full dashboard plus meal tools. Patients go straight to meal
                planning - simple, focused self-management.
              </Text>
            </article>
          </div>
        </section>

        <section id="roles" className="unified-landing-section unified-landing-section--alt" aria-labelledby="roles-title">
          <div className="unified-landing-section-head">
            <Heading level={2} id="roles-title" as="h2">Choose your path</Heading>
            <Text tone="muted">Same platform - tailored entry points after you sign in.</Text>
          </div>
          <div className="unified-landing-roles">
            <article className="unified-landing-role-card">
              <div className="unified-landing-role-icon" aria-hidden>
                <FiShield />
              </div>
              <Heading level={3} as="h3">Clinician</Heading>
              <Text as="p" tone="muted">Workspace, patients, insulin support, reports, alerts - and meal planning when you need it.</Text>
              <Link to="/login?role=clinician" className="unified-landing-role-cta">
                Continue as clinician <FiArrowRight size={16} aria-hidden />
              </Link>
            </article>
            <article className="unified-landing-role-card unified-landing-role-card--patient">
              <div className="unified-landing-role-icon unified-landing-role-icon--patient" aria-hidden>
                <FiCoffee />
              </div>
              <Heading level={3} as="h3">Patient</Heading>
              <Text as="p" tone="muted">Meal planning, food discovery, and glucose tools - without the clinical dashboard.</Text>
              <Link to="/login?role=patient" className="unified-landing-role-cta">
                Continue as patient <FiArrowRight size={16} aria-hidden />
              </Link>
            </article>
          </div>
        </section>

        <section className="unified-landing-cta-band" aria-labelledby="cta-band-title">
          <div className="unified-landing-cta-inner">
            <Heading level={2} id="cta-band-title" as="h2">Ready to open the portal?</Heading>
            <Text as="p">Use your demo credentials or the account your team issued.</Text>
            <Button as={Link} to="/login" className="unified-btn unified-btn-on-dark unified-btn-lg">
              Sign in to GlucoSense
              <FiArrowRight className="unified-btn-icon" aria-hidden />
            </Button>
          </div>
        </section>

        <Text className="unified-landing-disclaimer" size="helper" tone="muted">
          <strong>Clinical safety:</strong> GlucoSense supports - but does not replace - professional medical
          judgment. Meal Plan information is for education and self-management; confirm any care changes with your
          health team.
        </Text>
      </main>

      <footer className="unified-landing-footer">
        <span className="unified-landing-footer-brand">
          <FiActivity size={18} aria-hidden /> GlucoSense
        </span>
        <span className="unified-landing-footer-meta">Clinical decision support &amp; nutrition</span>
      </footer>
    </div>
  )
}
