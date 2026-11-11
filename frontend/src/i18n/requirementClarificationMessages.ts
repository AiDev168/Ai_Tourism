import type { Locale } from './messages';

export const requirementClarificationMessages: Record<Locale, {
  budgetCurrency: string;
  relativeAnchor: string;
  relativeDeparture: string;
  fieldLabels: Record<string, string>;
  known: string;
  unresolved: string;
  ambiguous: string;
  evidence: string;
}> = {
  'fa-IR': {
    budgetCurrency: 'واحد پول بودجه را مشخص کنید؛ از متن نمی‌توان آن را تشخیص داد.',
    relativeAnchor: 'برای تبدیل زمان نسبی به تاریخ، تاریخ مرجع و منطقهٔ زمانی سفر را مشخص کنید.',
    relativeDeparture: '{days} روز دیگر؛ تاریخ دقیق هنوز مشخص نیست.',
    fieldLabels: { destination: 'مقصد', origin: 'مبدأ', relative_start_date: 'زمان حرکت', duration_days: 'مدت سفر', travel_dates: 'تاریخ سفر', travelers: 'همراهان', budget: 'بودجه', interests: 'علاقه‌ها', hard_constraints: 'الزامات', accessibility: 'دسترسی' },
    known: 'برداشت پیشنهادی', unresolved: 'نیازمند پاسخ', ambiguous: 'مبهم', evidence: 'عبارت متن',
  },
  'en-US': {
    budgetCurrency: 'Please specify the budget currency; it cannot be determined from your message.',
    relativeAnchor: 'Provide the trip reference date and timezone to resolve this relative departure date.',
    relativeDeparture: 'In {days} days; the calendar date is not resolved.',
    fieldLabels: { destination: 'Destination', origin: 'Origin', relative_start_date: 'Departure timing', duration_days: 'Trip duration', travel_dates: 'Travel dates', travelers: 'Travelers', budget: 'Budget', interests: 'Interests', hard_constraints: 'Requirements', accessibility: 'Accessibility' },
    known: 'Suggested interpretation', unresolved: 'Needs an answer', ambiguous: 'Ambiguous', evidence: 'Text evidence',
  },
  ar: {
    budgetCurrency: 'يرجى تحديد عملة الميزانية؛ لا يمكن استنتاجها من رسالتك.',
    relativeAnchor: 'حدّد تاريخ الرحلة المرجعي والمنطقة الزمنية لحساب موعد المغادرة النسبي.',
    relativeDeparture: 'بعد {days} أيام؛ لم يُحدّد التاريخ التقويمي.',
    fieldLabels: { destination: 'الوجهة', origin: 'نقطة الانطلاق', relative_start_date: 'موعد المغادرة', duration_days: 'مدة الرحلة', travel_dates: 'تواريخ السفر', travelers: 'المسافرون', budget: 'الميزانية', interests: 'الاهتمامات', hard_constraints: 'المتطلبات', accessibility: 'إمكانية الوصول' },
    known: 'فهم مقترح', unresolved: 'يتطلب إجابة', ambiguous: 'ملتبس', evidence: 'دليل من النص',
  },
};
