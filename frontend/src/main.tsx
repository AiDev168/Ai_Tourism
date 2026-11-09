import React from 'react';
import { createRoot } from 'react-dom/client';
import { LocaleProvider } from './i18n/LocaleContext';
import { App } from './pages/App';
import './styles.css';
import './offline.css';

async function clearStalePwaStateInDevelopment(): Promise<void> {
  if (!('serviceWorker' in navigator)) return;

  // A production PWA worker can keep serving a cached index.html on the same
  // localhost origin after switching to Vite dev. That stale HTML points to
  // hashed production assets which do not exist on the dev server.
  const registrations = await navigator.serviceWorker.getRegistrations();
  await Promise.all(registrations.map((registration) => registration.unregister()));

  if ('caches' in window) {
    const cacheNames = await window.caches.keys();
    await Promise.all(
      cacheNames
        .filter((name) => name.startsWith('rahgard-shell-'))
        .map((name) => window.caches.delete(name)),
    );
  }
}

async function bootstrap(): Promise<void> {
  if (import.meta.env.DEV) {
    try {
      await clearStalePwaStateInDevelopment();
    } catch (error) {
      console.warn('[Rahgard] Could not clear stale PWA state in development.', error);
    }
  }

  const rootElement = document.getElementById('root');
  if (!rootElement) {
    throw new Error('Application root element #root was not found.');
  }

  createRoot(rootElement).render(
    <React.StrictMode>
      <LocaleProvider>
        <App />
      </LocaleProvider>
    </React.StrictMode>,
  );
}

void bootstrap();

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    void navigator.serviceWorker.register('/sw.js');
  });
}
