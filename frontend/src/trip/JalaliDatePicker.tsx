import { useEffect, useMemo, useRef, useState } from 'react';
import type { Locale } from '../i18n/messages';
import {
  deviceCalendarDate, formatJalaaliDate, isoToJalaali, jalaaliMonthDays,
  jalaaliToIso, jalaaliWeekStartOffset, JALALI_MONTHS_FA, JALALI_WEEKDAYS_FA,
} from './jalaliDate';

const copy = {
  'fa-IR': { choose: 'انتخاب تاریخ شمسی', previous: 'ماه قبل', next: 'ماه بعد', gregorian: 'میلادی', hijri: 'هجری قمری', clear: 'پاک کردن تاریخ' },
  'en-US': { choose: 'Choose a Gregorian date', previous: 'Previous month', next: 'Next month', gregorian: 'Gregorian', hijri: 'Islamic Hijri', clear: 'Clear date' },
  ar: { choose: 'اختر تاريخاً ميلادياً', previous: 'الشهر السابق', next: 'الشهر التالي', gregorian: 'ميلادي', hijri: 'هجري', clear: 'مسح التاريخ' },
} as const;

const englishMonths = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const weekdays = {
  'fa-IR': JALALI_WEEKDAYS_FA,
  'en-US': ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
  ar: ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'],
} as const;

function moveMonth(year: number, month: number, delta: number) {
  const zeroBased = year * 12 + month - 1 + delta;
  return { year: Math.floor(zeroBased / 12), month: ((zeroBased % 12) + 12) % 12 + 1 };
}

function gregorianDateLabel(value: string, locale: Locale): string {
  if (!/^\d{4}-\d{2}-\d{2}$/u.test(value)) return '';
  const date = new Date(`${value}T00:00:00.000Z`);
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium', calendar: 'gregory', timeZone: 'UTC' }).format(date);
}

function hijriDateLabel(value: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/u.test(value)) return '';
  const date = new Date(`${value}T00:00:00.000Z`);
  return new Intl.DateTimeFormat('ar-SA-u-ca-islamic', { dateStyle: 'medium', timeZone: 'UTC' }).format(date);
}

export type JalaliDatePickerProps = {
  id: string;
  label: string;
  locale: Locale;
  value: string;
  onChange: (isoGregorianDate: string) => void;
  timeZone?: string;
};

export function JalaliDatePicker({ id, label, locale, value, onChange, timeZone }: JalaliDatePickerProps) {
  const fa = locale === 'fa-IR';
  const messages = copy[locale];
  const displayLocale = locale;
  const selectedJalali = fa ? isoToJalaali(value) : null;
  const todayJalali = isoToJalaali(deviceCalendarDate(timeZone ?? (fa ? 'Asia/Tehran' : undefined)))
    ?? isoToJalaali(new Date().toISOString().slice(0, 10))!;
  const initialMonth = selectedJalali ?? todayJalali;
  const [open, setOpen] = useState(false);
  const [view, setView] = useState({ year: initialMonth.jy, month: initialMonth.jm });
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (event.target instanceof Node && !rootRef.current?.contains(event.target)) setOpen(false);
    };
    const onEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') setOpen(false); };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onEscape);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onEscape);
    };
  }, [open]);

  useEffect(() => {
    if (selectedJalali) setView({ year: selectedJalali.jy, month: selectedJalali.jm });
  }, [value]);

  const days = useMemo(() => {
    if (!fa) return [];
    const count = jalaaliMonthDays(view.year, view.month);
    const offset = jalaaliWeekStartOffset(view.year, view.month);
    return Array.from({ length: 42 }, (_, index) => {
      const day = index - offset + 1;
      return day >= 1 && day <= count ? day : null;
    });
  }, [fa, view.year, view.month]);

  const selectedText = value
    ? (fa ? formatJalaaliDate(value, locale) : gregorianDateLabel(value, locale))
    : messages.choose;
  const monthTitle = fa
    ? `${JALALI_MONTHS_FA[view.month - 1]} ${new Intl.NumberFormat('fa-IR', { useGrouping: false }).format(view.year)}`
    : `${englishMonths[view.month - 1]} ${view.year}`;

  if (!fa) {
    return <div className="travel-date-field">
      <label htmlFor={id}>{label}</label>
      <input id={id} type="date" value={value} onChange={event => onChange(event.currentTarget.value)} />
    </div>;
  }

  const chooseDay = (day: number) => {
    const iso = jalaaliToIso({ jy: view.year, jm: view.month, jd: day });
    if (iso) onChange(iso);
    setOpen(false);
  };
  const number = (value: number) => new Intl.NumberFormat(displayLocale, { useGrouping: false }).format(value);

  return <div className="travel-date-field jalali-date-field" ref={rootRef} dir="rtl">
    <span className="travel-date-label" id={`${id}-label`}>{label}</span>
    <input type="hidden" id={id} value={value} readOnly />
    <button id={`${id}-picker`} className="jalali-date-trigger" type="button"
      aria-labelledby={`${id}-label ${id}-picker`} aria-haspopup="dialog" aria-expanded={open}
      onClick={() => {
        const current = selectedJalali ?? todayJalali;
        setView({ year: current.jy, month: current.jm });
        setOpen(value => !value);
      }}>
      <span>{selectedText}</span><span aria-hidden="true">▦</span>
    </button>
    {value && <small className="jalali-gregorian-equivalent">{messages.gregorian}: {gregorianDateLabel(value, locale)} · {messages.hijri}: {hijriDateLabel(value)}</small>}
    {open && <div className="jalali-calendar" role="dialog" aria-modal="false" aria-label={monthTitle}>
      <div className="jalali-calendar-heading">
        <button type="button" aria-label={messages.previous} onClick={() => setView(current => moveMonth(current.year, current.month, -1))}>‹</button>
        <strong aria-live="polite">{monthTitle}</strong>
        <button type="button" aria-label={messages.next} onClick={() => setView(current => moveMonth(current.year, current.month, 1))}>›</button>
      </div>
      <div className="jalali-calendar-grid" role="grid" aria-label={monthTitle}>
        {weekdays['fa-IR'].map((weekday, index) => <span role="columnheader" key={`${weekday}-${index}`}>{weekday}</span>)}
        {days.map((day, index) => day === null
          ? <span aria-hidden="true" role="gridcell" key={`empty-${index}`} />
          : <button role="gridcell" type="button" key={day}
            aria-label={`${JALALI_WEEKDAYS_FA[index % 7]} ${number(day)} ${JALALI_MONTHS_FA[view.month - 1]} ${number(view.year)}`}
            aria-pressed={Boolean(selectedJalali && selectedJalali.jy === view.year && selectedJalali.jm === view.month && selectedJalali.jd === day)}
            onClick={() => chooseDay(day)}>{number(day)}</button>)}
      </div>
      {value && <button className="jalali-clear-date" type="button" onClick={() => { onChange(''); setOpen(false); }}>{messages.clear}</button>}
    </div>}
  </div>;
}
