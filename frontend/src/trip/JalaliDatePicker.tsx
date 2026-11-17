import { useEffect, useMemo, useRef, useState } from 'react';
import type { Locale } from '../i18n/messages';
import {
  deviceCalendarDate, formatJalaaliDate, isoToJalaali, jalaaliMonthDays, parseIsoCalendarDate,
  jalaaliToIso, jalaaliWeekStartOffset, JALALI_MONTHS_FA, JALALI_WEEKDAYS_FA,
} from './jalaliDate';

const copy = {
  'fa-IR': { choose: 'انتخاب تاریخ شمسی', previous: 'ماه قبل', next: 'ماه بعد', gregorian: 'میلادی', hijri: 'هجری قمری', clear: 'پاک کردن تاریخ' },
  'en-US': { choose: 'Choose a Gregorian date', previous: 'Previous month', next: 'Next month', gregorian: 'Gregorian', hijri: 'Islamic Hijri', clear: 'Clear date' },
  ar: { choose: 'اختر تاريخاً ميلادياً', previous: 'الشهر السابق', next: 'الشهر التالي', gregorian: 'ميلادي', hijri: 'هجري', clear: 'مسح التاريخ' },
} as const;

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
  const todayIso = deviceCalendarDate(timeZone ?? (fa ? 'Asia/Tehran' : undefined));
  const selectedJalali = fa ? isoToJalaali(value) : null;
  const selectedGregorian = parseIsoCalendarDate(value);
  const todayJalali = isoToJalaali(todayIso)!;
  const todayGregorian = parseIsoCalendarDate(todayIso)!;
  const initialView = fa
    ? { year: (selectedJalali ?? todayJalali).jy, month: (selectedJalali ?? todayJalali).jm }
    : { year: (selectedGregorian ?? todayGregorian).gy, month: (selectedGregorian ?? todayGregorian).gm };
  const [open, setOpen] = useState(false);
  const [view, setView] = useState(initialView);
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
    // Switching locale must switch calendar years even when no date is set.
    const jalali = selectedJalali ?? todayJalali;
    const gregorian = selectedGregorian ?? todayGregorian;
    setView(fa ? { year: jalali.jy, month: jalali.jm }
      : { year: gregorian.gy, month: gregorian.gm });
  }, [value, locale, timeZone]);

  const days = useMemo(() => {
    const count = fa ? jalaaliMonthDays(view.year, view.month)
      : new Date(Date.UTC(view.year, view.month, 0)).getUTCDate();
    const offset = fa ? jalaaliWeekStartOffset(view.year, view.month)
      : new Date(Date.UTC(view.year, view.month - 1, 1)).getUTCDay();
    return Array.from({ length: 42 }, (_, index) => {
      const day = index - offset + 1;
      return day >= 1 && day <= count ? day : null;
    });
  }, [fa, view.year, view.month]);

  const selectedText = value
    ? (fa ? formatJalaaliDate(value, locale) : gregorianDateLabel(value, locale))
    : messages.choose;
  const gregorianMonthLabel = new Intl.DateTimeFormat(locale, {
    month: 'long', year: 'numeric', calendar: 'gregory', timeZone: 'UTC',
  }).format(new Date(Date.UTC(view.year, view.month - 1, 15)));
  const monthTitle = fa
    ? `${JALALI_MONTHS_FA[view.month - 1]} ${new Intl.NumberFormat('fa-IR', { useGrouping: false }).format(view.year)}`
    : gregorianMonthLabel;

  const chooseDay = (day: number) => {
    const iso = fa ? jalaaliToIso({ jy: view.year, jm: view.month, jd: day })
      : `${String(view.year).padStart(4, '0')}-${String(view.month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    if (iso) onChange(iso);
    setOpen(false);
  };
  const number = (value: number) => new Intl.NumberFormat(displayLocale, { useGrouping: false }).format(value);

  return <div className="travel-date-field jalali-date-field" ref={rootRef} dir={fa ? 'rtl' : locale === 'ar' ? 'rtl' : 'ltr'}>
    <span className="travel-date-label" id={`${id}-label`}>{label}</span>
    <input type="hidden" id={id} value={value} readOnly />
    <button id={`${id}-picker`} className="jalali-date-trigger" type="button"
      aria-labelledby={`${id}-label ${id}-picker`} aria-haspopup="dialog" aria-expanded={open}
      onClick={() => {
        setView(fa
          ? { year: (selectedJalali ?? todayJalali).jy, month: (selectedJalali ?? todayJalali).jm }
          : { year: (selectedGregorian ?? todayGregorian).gy, month: (selectedGregorian ?? todayGregorian).gm });
        setOpen(value => !value);
      }}>
      <span>{selectedText}</span><span aria-hidden="true">▦</span>
    </button>
    {fa && value && <small className="jalali-gregorian-equivalent">{messages.gregorian}: {gregorianDateLabel(value, locale)} · {messages.hijri}: {hijriDateLabel(value)}</small>}
    {open && <div className="jalali-calendar" role="dialog" aria-modal="false" aria-label={monthTitle}>
      <div className="jalali-calendar-heading">
        <button type="button" aria-label={messages.previous} onClick={() => setView(current => moveMonth(current.year, current.month, -1))}>‹</button>
        <strong aria-live="polite">{monthTitle}</strong>
        <button type="button" aria-label={messages.next} onClick={() => setView(current => moveMonth(current.year, current.month, 1))}>›</button>
      </div>
      <div className="jalali-calendar-grid" role="grid" aria-label={monthTitle}>
        {weekdays[locale].map((weekday, index) => <span role="columnheader" key={`${weekday}-${index}`}>{weekday}</span>)}
        {days.map((day, index) => day === null
          ? <span aria-hidden="true" role="gridcell" key={`empty-${index}`} />
          : <button role="gridcell" type="button" key={day}
            aria-label={`${weekdays[locale][index % 7]} ${number(day)} ${monthTitle}`}
            aria-current={fa
              ? (todayJalali.jy === view.year && todayJalali.jm === view.month && todayJalali.jd === day ? 'date' : undefined)
              : (todayGregorian.gy === view.year && todayGregorian.gm === view.month && todayGregorian.gd === day ? 'date' : undefined)}
            aria-pressed={fa
              ? Boolean(selectedJalali && selectedJalali.jy === view.year && selectedJalali.jm === view.month && selectedJalali.jd === day)
              : Boolean(selectedGregorian && selectedGregorian.gy === view.year && selectedGregorian.gm === view.month && selectedGregorian.gd === day)}
            onClick={() => chooseDay(day)}>{number(day)}</button>)}
      </div>
      {value && <button className="jalali-clear-date" type="button" onClick={() => { onChange(''); setOpen(false); }}>{messages.clear}</button>}
    </div>}
  </div>;
}
