import type { Locale } from '../i18n/messages';

// Explicit display whitelist: private provenance, consent decisions and internal
// status/field codes must never leak into the public-facing request card.
const labels: Record<Locale, Record<string, string>> = {
  'fa-IR': {
    destinations: 'مقصد سفر', duration_days: 'مدت سفر (روز)', origin: 'مبدأ',
    travel_dates: 'تاریخ‌های سفر', traveler_count: 'تعداد مسافران',
    budget: 'بودجهٔ گفته‌شده', interests: 'علایق',
    travel_difficulty: 'درجهٔ سختی', weather_preferences: 'ترجیحات آب‌وهوا',
    local_cuisine: 'غذای محلی', soft_preferences: 'ترجیحات دیگر',
    constraints: 'محدودیت‌ها', accessibility: 'نیازهای دسترس‌پذیری',
  },
  'en-US': {
    destinations: 'Destinations', duration_days: 'Trip length (days)', origin: 'Origin',
    travel_dates: 'Travel dates', traveler_count: 'Travelers', budget: 'Stated budget',
    interests: 'Interests', travel_difficulty: 'Difficulty preferences',
    weather_preferences: 'Weather preferences', local_cuisine: 'Local cuisine',
    soft_preferences: 'Other preferences', constraints: 'Constraints', accessibility: 'Accessibility',
  },
  ar: {
    destinations: 'الوجهات', duration_days: 'مدة الرحلة (أيام)', origin: 'نقطة الانطلاق',
    travel_dates: 'تواريخ السفر', traveler_count: 'عدد المسافرين', budget: 'الميزانية المذكورة',
    interests: 'الاهتمامات', travel_difficulty: 'صعوبة المسار',
    weather_preferences: 'تفضيلات الطقس', local_cuisine: 'المأكولات المحلية',
    soft_preferences: 'تفضيلات إضافية', constraints: 'القيود', accessibility: 'إمكانية الوصول',
  },
};
const shownOrder = Object.keys(labels['fa-IR']);
const none: Record<Locale, string> = { 'fa-IR': 'مشخص نشده', 'en-US': 'Not specified', ar: 'غير محدد' };

function safeText(value: unknown, locale: Locale): string | null {
  if (typeof value === 'number' && Number.isFinite(value)) return String(value);
  if (typeof value === 'string') return value.trim() || null;
  if (Array.isArray(value)) {
    const items = value.filter(item => typeof item === 'string' && item.trim()).slice(0, 30);
    return items.length ? items.join(locale === 'en-US' ? ', ' : '، ') : null;
  }
  return null;
}

export function displayPartnerRequest(requirements: Record<string, unknown>, locale: Locale) {
  return shownOrder.map(key => {
    const value = requirements[key];
    let text: string | null = null;
    if (key === 'travel_dates' && value && typeof value === 'object' && !Array.isArray(value)) {
      const dates = value as Record<string, unknown>;
      const start = safeText(dates.start, locale);
      const end = safeText(dates.end, locale);
      text = start && end ? `${start} – ${end}` : start ?? end;
    } else if (key === 'budget' && value && typeof value === 'object' && !Array.isArray(value)) {
      const budget = value as Record<string, unknown>;
      text = safeText(budget.raw, locale)
        ?? ([safeText(budget.amount, locale), safeText(budget.currency, locale)].filter(Boolean).join(' ') || null);
    } else {
      text = safeText(value, locale);
    }
    return { key, label: labels[locale][key], text: text ?? none[locale], provided: text !== null };
  });
}
