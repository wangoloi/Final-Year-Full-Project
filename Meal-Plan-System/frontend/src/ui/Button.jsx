import React from 'react';
import { cx } from './cx';

export default function Button({
  as: Tag = 'button',
  variant = 'primary', // primary | secondary | ghostOnDark
  size = 'md', // md | sm
  block = false,
  className,
  children,
  ...props
}) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-lg border border-transparent no-underline transition-all duration-200 ease-in-out focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-60';

  const sizeClass =
    size === 'sm' ? 'px-[0.65rem] py-1.5 text-[0.875rem]' : 'px-5 py-3 text-button';

  const variantClass =
    variant === 'secondary'
      ? 'bg-gray-200 text-gray-900 hover:-translate-y-px hover:bg-gray-300 hover:shadow-card'
      : variant === 'ghostOnDark'
        ? 'border-white/60 bg-transparent text-white hover:border-white hover:bg-white/10'
        : 'bg-blue-600 text-white hover:-translate-y-px hover:bg-blue-700 hover:shadow-card-lg';

  return (
    <Tag className={cx(base, sizeClass, variantClass, block && 'w-full', className)} {...props}>
      {children}
    </Tag>
  );
}

