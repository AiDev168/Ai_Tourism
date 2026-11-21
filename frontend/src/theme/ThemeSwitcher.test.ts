// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from 'vitest';
import { applyRahgardTheme, initialRahgardTheme } from './ThemeSwitcher';

describe('Rahgard day/night theme', () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute('data-rahgard-theme');
    document.head.innerHTML = '<meta name="theme-color" content="#f6f7fb" />';
  });
  it('restores user-selected light or dark theme from local storage', () => {
    window.localStorage.setItem('rahgard-theme-v2', 'dark');
    expect(initialRahgardTheme()).toBe('dark');
    window.localStorage.setItem('rahgard-theme-v2', 'light');
    expect(initialRahgardTheme()).toBe('light');
  });
  it('updates root theme, native inputs and PWA browser header color together', () => {
    applyRahgardTheme('dark');
    expect(document.documentElement.dataset.rahgardTheme).toBe('dark');
    expect(document.documentElement.style.colorScheme).toBe('dark');
    expect(document.querySelector('meta[name="theme-color"]')?.getAttribute('content')).toBe('#0b101d');
    applyRahgardTheme('light');
    expect(document.documentElement.dataset.rahgardTheme).toBe('light');
    expect(document.querySelector('meta[name="theme-color"]')?.getAttribute('content')).toBe('#f6f7fb');
  });
});
