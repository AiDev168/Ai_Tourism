import type { Locale } from '../i18n/messages';

const historical: Record<Locale, string> = {
  'fa-IR': 'جاهای تاریخی',
  'en-US': 'Historic places',
  ar: 'المعالم التاريخية',
};

export function displayTripInterest(value: string, locale: Locale): string {
  return value === 'historical_attractions' ? historical[locale] : value;
}

export function reviewedTripInterests(text: string): string[] {
  const names = text.split(/[,،؛;]/u).map(value => value.trim()).filter(Boolean);
  return [...new Set(names.map(value =>
    value === 'historical_attractions' || Object.values(historical).some(label => label === value)
      ? 'historical_attractions' : value))];
}
