import React from 'react';
import { cx } from './cx';

export default function Text({
  as: Tag = 'p',
  size = 'body', // body | helper | caption
  tone = 'default', // default | muted | onDark
  className,
  children,
  ...props
}) {
  const sizeClass = size === 'caption' ? 'text-caption' : size === 'helper' ? 'text-helper' : 'text-base';
  const toneClass =
    tone === 'muted' ? 'text-slate-700' : tone === 'onDark' ? 'text-white' : 'text-slate-900';

  return (
    <Tag className={cx('m-0', sizeClass, 'leading-relaxed', toneClass, className)} {...props}>
      {children}
    </Tag>
  );
}

