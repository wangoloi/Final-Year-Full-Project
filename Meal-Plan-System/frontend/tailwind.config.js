/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontSize: {
        // Typography system (rem-based; body = 16px)
        h1: ['2.125rem', { lineHeight: '1.2', letterSpacing: '-0.02em' }], // 34px
        h2: ['1.75rem', { lineHeight: '1.2', letterSpacing: '-0.02em' }],  // 28px
        h3: ['1.375rem', { lineHeight: '1.25', letterSpacing: '-0.02em' }], // 22px
        button: ['0.9375rem', { lineHeight: '1.25' }], // 15px
        caption: ['0.8125rem', { lineHeight: '1.45' }], // 13px
        helper: ['0.875rem', { lineHeight: '1.45' }], // 14px
      },
      fontFamily: {
        sans: ['DM Sans', 'system-ui', '-apple-system', 'sans-serif'],
        outfit: ['Outfit', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.1)',
        'card-md': '0 4px 6px rgba(0,0,0,0.07)',
        'card-lg': '0 4px 12px rgba(0,0,0,0.15)',
        'card-xl': '0 10px 25px rgba(0,0,0,0.1)',
        'header-chat': '0 4px 14px rgba(0, 0, 0, 0.12)',
        'chat-chrome': '0 2px 10px rgba(0, 0, 0, 0.06)',
      },
      borderRadius: {
        sm: '0.25rem',
        DEFAULT: '0.5rem',
        lg: '0.75rem',
        xl: '1rem',
      },
    },
  },
  plugins: [],
};
