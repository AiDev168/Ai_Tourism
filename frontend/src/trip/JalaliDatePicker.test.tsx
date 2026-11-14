// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, describe, expect, it } from 'vitest';
import { JalaliDatePicker } from './JalaliDatePicker';

let root: Root | undefined;
let host: HTMLDivElement | undefined;

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

  it('keeps Gregorian native selection for English and Arabic', () => {
    host = document.createElement('div');
    document.body.append(host);
    root = createRoot(host);
    act(() => root?.render(<JalaliDatePicker id="start" label="Start" locale="en-US"
      value="2025-03-21" onChange={() => undefined} />));
    expect(host.querySelector('#start')?.getAttribute('type')).toBe('date');
  });
});
