import { useEffect, useState } from 'react';
import type { Locale } from '../i18n/messages';

export type RahgardTheme = 'light' | 'dark';
const storageKey = 'rahgard-theme-v2';
const lightColor = '#f6f7fb';
const darkColor = '#0b101d';

export function initialRahgardTheme(): RahgardTheme {
  try {
    const stored = window.localStorage.getItem(storageKey);
    if (stored === 'light' || stored === 'dark') return stored;
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  } catch {
    return 'light';
  }
}

export function applyRahgardTheme(next: RahgardTheme): void {
  document.documentElement.dataset.rahgardTheme = next;
  document.documentElement.style.colorScheme = next;
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', next === 'dark' ? darkColor : lightColor);
}

export function ThemeSwitcher({ locale }: { locale: Locale }) {
  const [theme, setTheme] = useState<RahgardTheme>(initialRahgardTheme);

  useEffect(() => {
    applyRahgardTheme(theme);
    try { window.localStorage.setItem(storageKey, theme); } catch { /* Private mode may prevent persistence. */ }
  }, [theme]);

  const label = locale === 'fa-IR' ? 'حالت نمایش' : locale === 'ar' ? 'مظهر التطبيق' : 'Color theme';
  const other = theme === 'dark'
    ? (locale === 'fa-IR' ? 'روز' : locale === 'ar' ? 'فاتح' : 'Light')
    : (locale === 'fa-IR' ? 'شب' : locale === 'ar' ? 'داكن' : 'Dark');
  return <button type="button" className="rahgard-theme-toggle" aria-label={`${label}: ${other}`}
    title={`${label}: ${other}`} aria-pressed={theme === 'dark'}
    onClick={() => setTheme(current => current === 'dark' ? 'light' : 'dark')}>
    <span aria-hidden="true">{theme === 'dark' ? '☀' : '☾'}</span>
    <span>{other}</span>
  </button>;
}
