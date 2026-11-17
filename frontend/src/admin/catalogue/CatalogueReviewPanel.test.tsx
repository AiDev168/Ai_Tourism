// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { CatalogueReviewPanel } from './CatalogueReviewPanel';

let root: Root;
let host: HTMLDivElement;

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

async function settle() {
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
}

beforeEach(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  host = document.createElement('div');
  document.body.append(host);
  root = createRoot(host);
});

afterEach(() => {
  act(() => root.unmount());
  host.remove();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('catalogue archive upload', () => {
  it('uses an ASCII metadata header for an archive with a Persian filename', async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith('/archives')) return Promise.resolve(response({ batch_id: 'batch-test' }));
      return Promise.resolve(response({ items: [] }));
    });
    vi.stubGlobal('fetch', fetchMock);

    await act(async () => {
      root.render(<CatalogueReviewPanel locale="en-US" csrfToken="csrf-test" />);
    });
    await settle();

    const input = host.querySelector<HTMLInputElement>('input[type="file"]')!;
    const archive = new File(['archive bytes'], 'دیتابیس - توریسم.zip', { type: 'application/zip' });
    Object.defineProperty(input, 'files', { configurable: true, value: [archive] });
    await act(async () => { input.dispatchEvent(new Event('change', { bubbles: true })); });
    const uploadButton = [...host.querySelectorAll<HTMLButtonElement>('button.primary')][0]!;
    await act(async () => { uploadButton.click(); });
    await settle();

    const upload = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/archives'));
    expect(upload).toBeDefined();
    const init = upload![1] as RequestInit;
    expect(init.headers).toEqual({
      'Content-Type': 'application/zip',
      'X-Archive-Filename': 'owner-archive.zip',
      'X-CSRF-Token': 'csrf-test',
    });
    expect(init.body).toBe(archive);
    expect(host.querySelector('[role="alert"]')).toBeNull();
  });
});
