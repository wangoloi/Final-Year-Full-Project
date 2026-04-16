import React from 'react'
import styles from './typography.module.css'

function cx(...parts) {
  return parts.filter(Boolean).join(' ')
}

export default function Text({
  as: Tag = 'p',
  tone = 'default', // default | muted
  size = 'body', // body | helper | caption
  className,
  children,
  ...props
}) {
  const toneClass = tone === 'muted' ? styles.muted : ''
  const sizeClass = size === 'caption' ? styles.caption : size === 'helper' ? styles.helper : ''

  return (
    <Tag className={cx(styles.text, toneClass, sizeClass, className)} {...props}>
      {children}
    </Tag>
  )
}

