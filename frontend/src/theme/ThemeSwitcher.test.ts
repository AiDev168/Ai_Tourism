// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { applyRahgardTheme, initialRahgardTheme } from './ThemeSwitcher';

// Node's experimental global localStorage can be undefined without
// --localstorage-file, even when Vitest runs under jsdom. Exercise the browser
// storage contract with isolated per-test state, not Node's process storage.
function isolatedLocalStorage(): Storage {
  const entries = new Map<string, string>();
  return {
    get length() { return entries.size; },
    clear: () => { entries.clear(); },
    getItem: key => entries.get(key) ?? null,
    key: index => [...entries.keys()][index] ?? null,
    removeItem: key => { entries.delete(key); },
    setItem: (key, value) => { entries.set(key, value); },
  };
}

describe('Rahgard day/night theme', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', isolatedLocalStorage());
    window.localStorage.clear();
    document.documentElement.removeAttribute('data-rahgard-theme');
    document.head.innerHTML = '<meta name="theme-color" content="#f6f7fb" />';
  });
  afterEach(() => vi.unstubAllGlobals());

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
