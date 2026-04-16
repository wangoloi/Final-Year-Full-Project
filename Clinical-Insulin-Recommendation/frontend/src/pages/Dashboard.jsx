/**
 * Workspace home: overview and shortcuts (assessment lives on /workspace/assessment).
 */
import { Link } from 'react-router-dom'
import { FiTrendingUp, FiActivity, FiAlertTriangle, FiCoffee, FiArrowRight } from 'react-icons/fi'
import DashboardStatsRow from '../components/dashboard/DashboardStatsRow'
import { WORKSPACE_PATH } from '../constants'
import Heading from '../ui/Heading'
import Text from '../ui/Text'

const shortcutClass = 'dashboard-home-shortcut'

export default function Dashboard() {
  return (
    <div className="dashboard dashboard-home">
      <section className="dashboard-section">
        <div className="card dashboard-home-hero">
          <Heading level={1} className="dashboard-home-title">Welcome</Heading>
          <Text className="card-description dashboard-home-lead">
            Run insulin decision support from <strong>Assessment</strong>, manage patients, review trends, and open tools from the menu.
          </Text>
        </div>
      </section>

      <DashboardStatsRow />

      <section className="dashboard-section" aria-labelledby="quick-links-heading">
        <Heading level={2} id="quick-links-heading" className="section-heading">Quick links</Heading>
        <div className="dashboard-home-grid">
          <Link to={`${WORKSPACE_PATH}/glucose-trends`} className={`card ${shortcutClass}`}>
            <FiTrendingUp size={22} className="dashboard-home-shortcut-icon" aria-hidden />
            <span className="dashboard-home-shortcut-title">Glucose trends</span>
            <span className="dashboard-home-shortcut-desc">Charts and readings</span>
            <span className="dashboard-home-shortcut-cta">Open <FiArrowRight size={16} aria-hidden /></span>
          </Link>
          <Link to={`${WORKSPACE_PATH}/insulin-management`} className={`card ${shortcutClass}`}>
            <FiActivity size={22} className="dashboard-home-shortcut-icon" aria-hidden />
            <span className="dashboard-home-shortcut-title">Glucose &amp; dosage</span>
            <span className="dashboard-home-shortcut-desc">Insulin and glucose management</span>
            <span className="dashboard-home-shortcut-cta">Open <FiArrowRight size={16} aria-hidden /></span>
          </Link>
          <Link to={`${WORKSPACE_PATH}/alerts`} className={`card ${shortcutClass}`}>
            <FiAlertTriangle size={22} className="dashboard-home-shortcut-icon" aria-hidden />
            <span className="dashboard-home-shortcut-title">Alerts</span>
            <span className="dashboard-home-shortcut-desc">Critical notifications and actions</span>
            <span className="dashboard-home-shortcut-cta">Open <FiArrowRight size={16} aria-hidden /></span>
          </Link>
          <Link to={`${WORKSPACE_PATH}/meal-plan`} className={`card ${shortcutClass}`}>
            <FiCoffee size={22} className="dashboard-home-shortcut-icon" aria-hidden />
            <span className="dashboard-home-shortcut-title">Meal plan</span>
            <span className="dashboard-home-shortcut-desc">Embedded nutrition app</span>
            <span className="dashboard-home-shortcut-cta">Open <FiArrowRight size={16} aria-hidden /></span>
          </Link>
        </div>
      </section>
    </div>
  )
}
