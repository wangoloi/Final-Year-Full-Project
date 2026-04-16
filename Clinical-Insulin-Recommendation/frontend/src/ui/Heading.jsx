import React from 'react'
import styles from './typography.module.css'

function cx(...parts) {
  return parts.filter(Boolean).join(' ')
}

export default function Heading({
  level = 1,
  as,
  className,
  children,
  ...props
}) {
  const safeLevel = [1, 2, 3].includes(level) ? level : 1
  const Tag = as || `h${safeLevel}`
  const sizeClass = safeLevel === 1 ? styles.h1 : safeLevel === 2 ? styles.h2 : styles.h3

  return (
    <Tag className={cx(styles.heading, sizeClass, className)} {...props}>
      {children}
    </Tag>
  )
}

