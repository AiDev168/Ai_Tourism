import { useEffect, useState } from 'react';
import type { Locale } from '../i18n/messages';
import './pwaUpdate.css';

const labels: Record<Locale, { ready: string; update: string }> = {
  'fa-IR': { ready: 'نسخهٔ جدید راه‌گرد آماده است.', update: 'به‌روزرسانی برنامه' },
  'en-US': { ready: 'A new version of Rahgard is ready.', update: 'Update app' },
  ar: { ready: 'إصدار جديد من راه‌گرد جاهز.', update: 'تحديث التطبيق' },
};

export function PwaUpdateNotice({ locale }: { locale: Locale }) {
  const [waiting, setWaiting] = useState<ServiceWorker | null>(null);
  useEffect(() => {
    if (!('serviceWorker' in navigator) || !import.meta.env.PROD) return;
    let active = true;
    let refreshing = false;
    const changed = () => {
      if (!refreshing) {
        refreshing = true;
        window.location.reload();
      }
    };
    navigator.serviceWorker.addEventListener('controllerchange', changed);
    const onRegistration = (registration: ServiceWorkerRegistration) => {
      if (registration.waiting && navigator.serviceWorker.controller && active) {
        setWaiting(registration.waiting);
      }
      registration.addEventListener('updatefound', () => {
        const installing = registration.installing;
        installing?.addEventListener('statechange', () => {
          if (installing.state === 'installed' && navigator.serviceWorker.controller && active) {
            setWaiting(registration.waiting ?? installing);
          }
        });
      });
    };
    void navigator.serviceWorker.ready.then(onRegistration).catch(() => {});
    return () => {
      active = false;
      navigator.serviceWorker.removeEventListener('controllerchange', changed);
    };
  }, []);
  if (!waiting) return null;
  return <div className="pwa-update-notice" role="status" dir={locale === 'en-US' ? 'ltr' : 'rtl'}>
    <span>{labels[locale].ready}</span>
    <button type="button" onClick={() => waiting.postMessage({ type: 'SKIP_WAITING' })}>
      {labels[locale].update}
    </button>
  </div>;
}
