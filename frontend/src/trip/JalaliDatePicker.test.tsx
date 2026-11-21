// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { JalaliDatePicker } from './JalaliDatePicker';

let root: Root | undefined;
let host: HTMLDivElement | undefined;

beforeEach(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
});

afterEach(() => {
  if (root) act(() => root?.unmount());
  host?.remove();
  root = undefined;
  host = undefined;
});

describe('JalaliDatePicker', () => {
  it('selects a Jalali day and emits the existing Gregorian ISO contract', () => {
    const selected: string[] = [];
    host = document.createElement('div');
    document.body.append(host);
    root = createRoot(host);
    act(() => root?.render(<JalaliDatePicker id="start" label="تاریخ شروع" locale="fa-IR"
      value="2025-03-21" onChange={value => selected.push(value)} />));
    act(() => host?.querySelector<HTMLButtonElement>('#start-picker')?.click());
    const chosen = host?.querySelector<HTMLButtonElement>('[aria-pressed="true"]');
    expect(chosen?.textContent).toBe('۱');
    act(() => chosen?.click());
    expect(selected).toEqual(['2025-03-21']);
  });

  it.each(['en-US', 'ar'] as const)('renders a Gregorian calendar in %s', locale => {
    const selected: string[] = [];
    host = document.createElement('div');
    document.body.append(host);
    root = createRoot(host);
    act(() => root?.render(<JalaliDatePicker id="start" label="Start" locale={locale}
      value="2025-03-21" onChange={value => selected.push(value)} timeZone="UTC" />));
    act(() => host?.querySelector<HTMLButtonElement>('#start-picker')?.click());
    expect(host?.querySelectorAll('[role="columnheader"]').length).toBe(7);
    const chosen = host?.querySelector<HTMLButtonElement>('[aria-pressed="true"]');
    expect(chosen).toBeTruthy();
    act(() => chosen?.click());
    expect(selected).toEqual(['2025-03-21']);
  });

  it('resets the calendar year after language switching without a selected date', () => {
    host = document.createElement('div');
    document.body.append(host);
    root = createRoot(host);
    act(() => root?.render(<JalaliDatePicker id="start" label="Start" locale="en-US"
      value="" onChange={() => undefined} timeZone="UTC" />));
    act(() => host?.querySelector<HTMLButtonElement>('#start-picker')?.click());
    expect(host?.querySelector('.jalali-calendar-heading strong')?.textContent).toContain(String(new Date().getUTCFullYear()));
    act(() => root?.render(<JalaliDatePicker id="start" label="تاریخ شروع" locale="fa-IR"
      value="" onChange={() => undefined} timeZone="UTC" />));
    expect(host?.querySelector('.jalali-calendar-heading strong')?.textContent).not.toContain(String(new Date().getUTCFullYear()));
  });

  it('marks today separately from selected day in the traveler timezone', () => {
    host = document.createElement('div');
    document.body.append(host);
    root = createRoot(host);
    const today = new Date();
    const iso = new Intl.DateTimeFormat('en-CA', { timeZone: 'UTC', year: 'numeric', month: '2-digit', day: '2-digit' })
      .formatToParts(today);
    const components = Object.fromEntries(iso.map(item => [item.type, item.value]));
    const todayIso = `${components.year}-${components.month}-${components.day}`;
    act(() => root?.render(<JalaliDatePicker id="start" label="Start" locale="en-US"
      value={todayIso} onChange={() => undefined} timeZone="UTC" />));
    act(() => host?.querySelector<HTMLButtonElement>('#start-picker')?.click());
    expect(host?.querySelectorAll('button[aria-current="date"]').length).toBe(1);
    expect(host?.querySelector<HTMLButtonElement>('button[aria-current="date"]')?.getAttribute('aria-pressed')).toBe('true');
  });
});
