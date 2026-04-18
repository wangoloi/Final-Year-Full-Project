/**
 * GlucoSense wordmark image from `public/glucosense-logo.svg`.
 */
import { BRAND_LOGO_SRC } from '../constants'

export default function BrandLogo({ className = '', size = 40, title = 'GlucoSense' }) {
  return (
    <img
      src={BRAND_LOGO_SRC}
      width={size}
      height={size}
      className={className}
      alt=""
      title={title}
      decoding="async"
    />
  )
}
