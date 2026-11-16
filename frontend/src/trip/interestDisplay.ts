import type { Locale } from '../i18n/messages';

const historical: Record<Locale, string> = {
  'fa-IR': 'جاهای تاریخی',
  'en-US': 'Historic places',
  ar: 'المعالم التاريخية',
};
const gardens: Record<Locale, string> = {
  'fa-IR': '\u0628\u0627\u063a\u200c\u0647\u0627',
  'en-US': 'Gardens',
  ar: '\u0627\u0644\u062d\u062f\u0627\u0626\u0642',
};

export function displayTripInterest(value: string, locale: Locale): string {
  if (value === 'historical_attractions') return historical[locale];
  if (value === 'gardens') return gardens[locale];
  return value;
}

export function reviewedTripInterests(text: string): string[] {
  const names = text.split(/[,،؛;]/u).map(value => value.trim()).filter(Boolean);
  return [...new Set(names.map(value =>
    value === 'historical_attractions' || Object.values(historical).some(label => label === value)
      ? 'historical_attractions'
      : value === 'gardens' || Object.values(gardens).some(label => label === value) ? 'gardens' : value))];
}
