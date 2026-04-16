import React from 'react'
import styles from './button.module.css'

function cx(...parts) {
  return parts.filter(Boolean).join(' ')
}

export default function Button({
  as: Tag = 'button',
  variant = 'primary', // primary | secondary
  size = 'md', // md | sm
  block = false,
  className,
  children,
  ...props
}) {
  const variantClass = variant === 'secondary' ? styles.secondary : styles.primary
  const sizeClass = size === 'sm' ? styles.sm : ''
  const blockClass = block ? styles.block : ''

  return (
    <Tag
      className={cx(styles.button, variantClass, sizeClass, blockClass, className)}
      {...props}
    >
      {children}
    </Tag>
  )
}

