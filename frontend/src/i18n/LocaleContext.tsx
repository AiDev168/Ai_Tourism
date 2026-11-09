import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { direction, locales, messages, type Locale, type MessageKey } from './messages';
type LocaleApi = { locale: Locale; setLocale: (locale: Locale) => void; t: (key: MessageKey) => string };
const Context = createContext<LocaleApi | null>(null);
export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState<Locale>(() => {
    const saved = localStorage.getItem('locale');
    return locales.includes(saved as Locale) ? saved as Locale : 'fa-IR';
  });
  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = direction(locale);
    document.title = `${messages[locale].brand} | ${messages[locale].tagline}`;
    document.querySelector('meta[name="description"]')?.setAttribute('content', messages[locale].heroBody);
    localStorage.setItem('locale', locale);
  }, [locale]);
  const api = useMemo(() => ({ locale, setLocale, t: (key: MessageKey) => messages[locale][key] }), [locale]);
  return <Context.Provider value={api}>{children}</Context.Provider>;
}
export function useLocale() { const value = useContext(Context); if (!value) throw new Error('LocaleProvider missing'); return value; }
