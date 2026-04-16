import React from 'react';
import { cx } from './cx';

export default function Heading({
  level = 1,
  as,
  tone = 'default', // default | muted | onDark
  className,
  children,
  ...props
}) {
  const safeLevel = [1, 2, 3].includes(level) ? level : 1;
  const Tag = as || `h${safeLevel}`;

  const sizeClass = safeLevel === 1 ? 'text-h1' : safeLevel === 2 ? 'text-h2' : 'text-h3';
  const weightClass = safeLevel === 1 ? 'font-bold' : safeLevel === 2 ? 'font-bold' : 'font-semibold';
  const fontClass = safeLevel === 1 || safeLevel === 2 ? 'font-outfit' : 'font-outfit';

  const toneClass =
    tone === 'muted' ? 'text-slate-700' : tone === 'onDark' ? 'text-white' : 'text-slate-900';

  return (
    <Tag className={cx('m-0', fontClass, sizeClass, weightClass, 'tracking-tight', toneClass, className)} {...props}>
      {children}
    </Tag>
  );
}

