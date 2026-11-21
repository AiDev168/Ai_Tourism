import { useEffect, useRef, useState } from 'react';
import { formatNumber, type Locale } from '../i18n/messages';
import { tripMessages } from '../i18n/tripMessages';
import { requirementClarificationMessages } from '../i18n/requirementClarificationMessages';
import { destinationResolutionMessages } from '../i18n/destinationResolutionMessages';
import { createTripRequirements, MAX_TRIP_DURATION_DAYS, resolveRelativeTripDates, type TripRequirements } from '../trip/tripIntake';
import { travelerApi } from '../trip/travelerApi';
import { confirmDestinationCandidate, resolveDestinationNames, type DestinationResolution } from '../trip/destinationResolution';
import { ApiDestinationCatalogPort } from '../trip/destinationCatalogApi';
import { useLocale } from '../i18n/LocaleContext';
import { AuthPanel } from '../auth/AuthPanel';
import type { AuthSession } from '../auth/authApi';
import { TravelerJourney } from '../trip/TravelerJourney';
import { PwaUpdateNotice } from '../pwa/PwaUpdateNotice';
import { AiProviderAdminPanel } from '../admin/aiProviders/AiProviderAdminPanel';
import { displayTripInterest } from '../trip/interestDisplay';
import { deviceCalendarDate } from '../trip/jalaliDate';
import { requestDeviceOrigin, withApproximateDeviceOrigin } from './locationOrigin';
import { PartnerWorkspace } from '../partners/PartnerWorkspace';
import { ThemeSwitcher } from '../theme/ThemeSwitcher';
import { CatalogueReviewPanel } from '../admin/catalogue/CatalogueReviewPanel';

const destinationCatalog = new ApiDestinationCatalogPort();

type LocationMessageKey = 'unsupported' | 'requesting' | 'denied' | 'timeout' | 'unavailable' | 'invalid' | 'stale' | 'accuracy';
const locationMessages: Record<Locale, Record<LocationMessageKey, string> & { cityUnresolved: (accuracy: number) => string }> = {
  'fa-IR': {
    unsupported: '\u0627\u06cc\u0646 \u0645\u0631\u0648\u0631\u06af\u0631 \u0627\u0632 \u0645\u06a9\u0627\u0646\u200c\u06cc\u0627\u0628\u06cc \u067e\u0634\u062a\u06cc\u0628\u0627\u0646\u06cc \u0646\u0645\u06cc\u200c\u06a9\u0646\u062f.',
    requesting: '\u062f\u0631\u062e\u0648\u0627\u0633\u062a \u0627\u062c\u0627\u0632\u0647\u0654 \u0645\u06a9\u0627\u0646\u06cc\u0627\u0628\u06cc \u0627\u0632 \u0645\u0631\u0648\u0631\u06af\u0631\u2026',
    denied: '\u062f\u0631\u062e\u0648\u0627\u0633\u062a \u0645\u06a9\u0627\u0646 \u0631\u062f \u0634\u062f. \u0645\u06cc\u200c\u062a\u0648\u0627\u0646\u06cc\u062f \u0645\u0628\u062f\u0623 \u0631\u0627 \u062f\u0633\u062a\u06cc \u0648\u0627\u0631\u062f \u06a9\u0646\u06cc\u062f.',
    timeout: '\u062f\u0631\u06cc\u0627\u0641\u062a \u0645\u06a9\u0627\u0646 \u0628\u0647 \u0645\u0647\u0644\u062a \u0646\u0631\u0633\u06cc\u062f. \u062f\u0648\u0628\u0627\u0631\u0647 \u0627\u0645\u062a\u062d\u0627\u0646 \u06a9\u0646\u06cc\u062f \u06cc\u0627 \u0645\u0628\u062f\u0623 \u0631\u0627 \u0648\u0627\u0631\u062f \u06a9\u0646\u06cc\u062f.',
    unavailable: '\u0645\u06a9\u0627\u0646 \u062f\u0631 \u062f\u0633\u062a\u0631\u0633 \u0646\u06cc\u0633\u062a. \u0645\u06cc\u200c\u062a\u0648\u0627\u0646\u06cc\u062f \u0645\u0628\u062f\u0623 \u0631\u0627 \u062f\u0633\u062a\u06cc \u0648\u0627\u0631\u062f \u06a9\u0646\u06cc\u062f.',
    invalid: '\u062f\u0633\u062a\u06af\u0627\u0647 \u0645\u0648\u0642\u0639\u06cc\u062a \u0645\u0639\u062a\u0628\u0631\u06cc \u0646\u0641\u0631\u0633\u062a\u0627\u062f. \u0645\u0628\u062f\u0623 \u0631\u0627 \u062f\u0633\u062a\u06cc \u0648\u0627\u0631\u062f \u06a9\u0646\u06cc\u062f.',
    stale: '\u0645\u0648\u0642\u0639\u06cc\u062a \u062f\u0631\u06cc\u0627\u0641\u062a\u06cc \u0642\u062f\u06cc\u0645\u06cc \u0627\u0633\u062a. \u062f\u0648\u0628\u0627\u0631\u0647 \u0627\u0645\u062a\u062d\u0627\u0646 \u06a9\u0646\u06cc\u062f.',
    accuracy: '\u062f\u0642\u062a \u0645\u06a9\u0627\u0646 \u0628\u0631\u0627\u06cc \u067e\u06cc\u0634\u0646\u0647\u0627\u062f \u0645\u0628\u062f\u0623 \u06a9\u0627\u0641\u06cc \u0646\u06cc\u0633\u062a. \u0645\u0628\u062f\u0623 \u0631\u0627 \u062f\u0633\u062a\u06cc \u0648\u0627\u0631\u062f \u06a9\u0646\u06cc\u062f.',
    cityUnresolved: accuracy => `\u0646\u0642\u0637\u0647\u0654 \u0645\u0628\u062f\u0623 \u062a\u0642\u0631\u06cc\u0628\u06cc \u067e\u06cc\u0634\u0646\u0647\u0627\u062f \u0634\u062f (\u062f\u0642\u062a \u06af\u0632\u0627\u0631\u0634\u200c\u0634\u062f\u0647 \u062d\u062f\u0648\u062f \u00b1${accuracy} \u0645\u062a\u0631). \u0634\u0647\u0631 \u062a\u0634\u062e\u06cc\u0635 \u062f\u0627\u062f\u0647 \u0646\u0634\u062f\u0647\u061b \u0645\u0628\u062f\u0623 \u0631\u0627 \u062f\u0631 \u0641\u0631\u0645 \u0628\u0631\u0631\u0633\u06cc \u06a9\u0646\u06cc\u062f.`,
  },
  'en-US': {
    unsupported: 'This browser does not support location. You can enter an origin manually.',
    requesting: 'Requesting device location permission…',
    denied: 'Location permission was denied. You can enter an origin manually.',
    timeout: 'Location lookup timed out. Try again or enter an origin manually.',
    unavailable: 'Device location is unavailable. You can enter an origin manually.',
    invalid: 'The device returned an invalid position. Enter an origin manually.',
    stale: 'The device position is too old. Try again.',
    accuracy: 'The reported location is too imprecise to suggest an origin.',
    cityUnresolved: accuracy => `Approximate departure point suggested (reported accuracy about ±${accuracy} m). City could not be verified; review this origin in the trip form.`,
  },
  ar: {
    unsupported: '\u0647\u0630\u0627 \u0627\u0644\u0645\u062a\u0635\u0641\u062d \u0644\u0627 \u064a\u062f\u0639\u0645 \u062a\u062d\u062f\u064a\u062f \u0627\u0644\u0645\u0648\u0642\u0639. \u064a\u0645\u0643\u0646\u0643 \u0625\u062f\u062e\u0627\u0644 \u0645\u0646\u0637\u0644\u0642 \u064a\u062f\u0648\u064a\u0627\u064b.',
    requesting: '\u062c\u0627\u0631\u064d \u0637\u0644\u0628 \u0625\u0630\u0646 \u0627\u0644\u0645\u0648\u0642\u0639 \u0645\u0646 \u0627\u0644\u0645\u062a\u0635\u0641\u062d\u2026',
    denied: '\u0631\u064f\u0641\u0636 \u0625\u0630\u0646 \u0627\u0644\u0645\u0648\u0642\u0639. \u064a\u0645\u0643\u0646\u0643 \u0625\u062f\u062e\u0627\u0644 \u0645\u0646\u0637\u0644\u0642 \u064a\u062f\u0648\u064a\u0627\u064b.',
    timeout: '\u0627\u0646\u062a\u0647\u0644\u062a \u0645\u0647\u0644\u0629 \u062a\u062d\u062f\u064a\u062f \u0627\u0644\u0645\u0648\u0642\u0639. \u062d\u0627\u0648\u0644 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649 \u0623\u0648 \u0623\u062f\u062e\u0644 \u0645\u0646\u0637\u0644\u0642\u0627\u064b \u064a\u062f\u0648\u064a\u0627\u064b.',
    unavailable: '\u0627\u0644\u0645\u0648\u0642\u0639 \u063a\u064a\u0631 \u0645\u062a\u0627\u062d. \u064a\u0645\u0643\u0646\u0643 \u0625\u062f\u062e\u0627\u0644 \u0645\u0646\u0637\u0644\u0642 \u064a\u062f\u0648\u064a\u0627\u064b.',
    invalid: '\u0623\u0631\u0633\u0644 \u0627\u0644\u062c\u0647\u0627\u0632 \u0645\u0648\u0642\u0639\u0627\u064b \u063a\u064a\u0631 \u0635\u0627\u0644\u062d. \u0623\u062f\u062e\u0644 \u0627\u0644\u0645\u0646\u0637\u0644\u0642 \u064a\u062f\u0648\u064a\u0627\u064b.',
    stale: '\u0645\u0648\u0642\u0639 \u0627\u0644\u062c\u0647\u0627\u0632 \u0642\u062f\u064a\u0645. \u062d\u0627\u0648\u0644 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649.',
    accuracy: '\u062f\u0642\u0629 \u0627\u0644\u0645\u0648\u0642\u0639 \u063a\u064a\u0631 \u0643\u0627\u0641\u064a\u0629 \u0644\u0627\u0642\u062a\u0631\u0627\u062d \u0645\u0646\u0637\u0644\u0642.',
    cityUnresolved: accuracy => `\u0627\u0642\u062a\u064f\u0631\u062d\u062a \u0646\u0642\u0637\u0629 \u0627\u0646\u0637\u0644\u0627\u0642 \u062a\u0642\u0631\u064a\u0628\u064a\u0629 (\u0627\u0644\u062f\u0642\u0629 \u0627\u0644\u0645\u0628\u0644\u0651\u063a \u0639\u0646\u0647\u0627 \u062d\u0648\u0627\u0644\u064a \u00b1${accuracy} \u0645\u062a\u0631). \u0644\u0645 \u064a\u064f\u062a\u062d\u0642\u0642 \u0645\u0646 \u0627\u0644\u0645\u062f\u064a\u0646\u0629\u061b \u0631\u0627\u062c\u0639 \u0627\u0644\u0645\u0646\u0637\u0644\u0642 \u0641\u064a \u0627\u0644\u0646\u0645\u0648\u0630\u062c.`,
  },
};

const languageName: Record<Locale, string> = { 'fa-IR': 'فارسی', 'en-US': 'English', ar: 'العربية' };
const plannerCopy: Record<Locale, { title: string; intro: string; next: string; budgetScope: string }> = {
  'fa-IR': {
    title: 'سفرت را با گفت‌وگو بساز',
    intro: 'خواسته‌هایت را بنویس. آنچه فهمیده‌ایم را می‌بینی، به سؤال‌های کوتاه پاسخ می‌دهی و پیش از پیشنهاد یا برنامه، خودت اطلاعات سفر را تأیید می‌کنی.',
    next: 'ادامهٔ گفت‌وگو و بررسی سفر',
    budgetScope: 'هنوز مشخص نیست این بودجه برای کل سفر است یا هر نفر؛ پیش از اتکا به هزینه، آن را روشن کنید.',
  },
  'en-US': {
    title: 'Plan your trip through conversation',
    intro: 'Describe what you need, review what we understood, answer short questions, and confirm your trip before suggestions or a plan.',
    next: 'Continue the conversation',
    budgetScope: 'We do not yet know whether this budget is for the whole trip or per person. Clarify it before relying on costs.',
  },
  ar: {
    title: 'خطط رحلتك عبر المحادثة',
    intro: 'اكتب احتياجاتك، وراجع ما فهمناه، وأجب عن أسئلة قصيرة، ثم أكد تفاصيل الرحلة قبل عرض الاقتراحات أو الخطة.',
    next: 'تابع المحادثة ومراجعة الرحلة',
    budgetScope: 'لم يتضح بعد ما إذا كانت الميزانية للرحلة كلها أم لكل شخص؛ وضح ذلك قبل الاعتماد على التكلفة.',
  },
};

const photos = {
  hero: '/images/naghshe-jahan-1280.webp',
  kashan: '/images/fin-garden-1280.webp',
  yazd: '/images/yazd-windcatchers-1280.webp',
  qeshm: '/images/qeshm-hara-1280.webp'
};

const photoSources = {
  hero: 'https://commons.wikimedia.org/wiki/File:Naqsh-e_Jahan_Square,_Isfahan_02.jpg',
  kashan: 'https://commons.wikimedia.org/wiki/File:Fin_Garden,_Kashan,_Iran.jpg',
  yazd: 'https://commons.wikimedia.org/wiki/File:Windcatchers_in_Yazd.jpg',
  qeshm: 'https://commons.wikimedia.org/wiki/File:Hara_forests_of_Qeshm_-_1.jpg'
};

function PhotoCredit({ source, author, label }: { source: string; author: string; label: string }) {
  return (
    <span className="photo-credit">
      <a href={source} target="_blank" rel="noreferrer">{label}: {author}</a>
      <span aria-hidden="true"> · </span>
      <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noreferrer">CC BY-SA 4.0</a>
    </span>
  );
}

export function App() {
  const { locale, setLocale, t } = useLocale();
  const [requirements, setRequirements] = useState<TripRequirements | null>(null);
  const [destinationResolution, setDestinationResolution] = useState<DestinationResolution | null>(null);
  const [catalogueLoading, setCatalogueLoading] = useState(false);
  const [clarifications, setClarifications] = useState<TripRequirements['missingRequired']>([]);
  const [ambiguities, setAmbiguities] = useState<TripRequirements['ambiguousRequired']>([]);
  const [error, setError] = useState('');
  const [heroImageFailed, setHeroImageFailed] = useState(false);
  const [authSession, setAuthSession] = useState<AuthSession | null>(null);
  const [online, setOnline] = useState(navigator.onLine);
  // Smart conversation is the default workflow; no separate opt-in checkbox.
  const [suggestedOrigin, setSuggestedOrigin] = useState<{ approximateText: string; accuracyMeters: number } | null>(null);
  const [, setLocationStatus] = useState('');
  const [travelerTimezone, setTravelerTimezone] = useState(() =>
    Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');
  const requestDeviceLocation = () => {
    if (!navigator.geolocation) {
      setLocationStatus(locationMessages[locale].unsupported);
      return;
    }
    setLocationStatus(locationMessages[locale].requesting);
    void requestDeviceOrigin(navigator.geolocation).then(result => {
      if (result.kind === 'rejected') {
        setLocationStatus(locationMessages[locale][result.reason]);
        return;
      }
      // No trusted offline city index is available. Only the coarse,
      // explicitly approximate point enters application state.
      setSuggestedOrigin(result.origin);
      setRequirements(current => current
        ? withApproximateDeviceOrigin(current, result.origin, locale)
        : current);
      setTravelerTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');
      setLocationStatus(locationMessages[locale].cityUnresolved(result.origin.accuracyMeters));
    });
  };
  useEffect(() => {
    // Auto-fill only when permission was already granted. Never trigger an
    // unrequested browser permission prompt; the visible button handles that.
    let active = true;
    if (!authSession || !navigator.permissions?.query) return;
    void navigator.permissions.query({ name: 'geolocation' }).then(permission => {
      if (active && permission.state === 'granted') requestDeviceLocation();
    }).catch(() => { /* Browsers may not support querying geolocation permissions. */ });
    return () => { active = false; };
  }, [authSession?.user.user_id]);
  const [assistantRouteState, setAssistantRouteState] = useState<'loading' | 'configured' | 'connected' | 'disabled' | 'unavailable' | 'quota_exhausted'>('loading');
  const [conversationVisible, setConversationVisible] = useState(false);
  const [assistantRemaining, setAssistantRemaining] = useState<number | null>(null);
  const manualDateOverrideRequestRef = useRef<string | null>(null);
  useEffect(() => {
    const today = deviceCalendarDate(travelerTimezone);
    setRequirements(current => !current || manualDateOverrideRequestRef.current === current.requestText
      ? current : resolveRelativeTripDates(current, today, travelerTimezone));
  }, [travelerTimezone]);
  const promptRef = useRef<HTMLTextAreaElement>(null);
  const requestTextRef = useRef('');
  const catalogueRequestVersion = useRef(0);

  const loadDestinationResolution = (phrases: readonly string[] | null, requestLocale: Locale) => {
    const requestVersion = ++catalogueRequestVersion.current;
    if (!phrases?.length) {
      setDestinationResolution(null);
      setCatalogueLoading(false);
      return;
    }
    setDestinationResolution(null);
    setCatalogueLoading(true);
    void destinationCatalog.load().then(catalogue => {
      if (catalogueRequestVersion.current !== requestVersion) return;
      setDestinationResolution(resolveDestinationNames(phrases, requestLocale, catalogue));
      setCatalogueLoading(false);
    }).catch(() => {
      if (catalogueRequestVersion.current !== requestVersion) return;
      setDestinationResolution(resolveDestinationNames(phrases, requestLocale, { kind: 'unavailable' }));
      setCatalogueLoading(false);
    });
  };

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);

  useEffect(() => {
    let current = true;
    if (!authSession || !online) {
      setAssistantRouteState(online ? 'disabled' : 'unavailable');
      setAssistantRemaining(null);
      return () => { current = false; };
    }
    setAssistantRouteState('loading');
    void travelerApi.assistantStatus().then(result => {
      if (!current) return;
      setAssistantRouteState(result.state);
      setAssistantRemaining(Math.min(result.user_remaining, result.global_remaining));
    }).catch(() => {
      if (current) { setAssistantRouteState('unavailable'); setAssistantRemaining(null); }
    });
    return () => { current = false; };
  }, [authSession?.user.user_id, online]);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    // Read the live form controls at the submit boundary. React state remains
    // useful for rendering, but it must not be the only source of submitted
    // text: FormData captures the exact values currently visible to the user.
    const formData = new FormData(event.currentTarget);
    const requestText = promptRef.current?.value ?? String(formData.get('requestText') ?? requestTextRef.current);
    manualDateOverrideRequestRef.current = null;
    const result = createTripRequirements({ requestText, locale });
    if (result.kind === 'invalid') {
      catalogueRequestVersion.current += 1;
      setCatalogueLoading(false);
      const messageKey = {
        'request-required': 'requestRequired',
        'request-too-long': 'requestTooLong',
        'duration-too-long': 'durationTooLong',
      } as const;
      setError(tripMessages[locale][messageKey[result.reason]].replace('{value}', formatNumber(locale, MAX_TRIP_DURATION_DAYS)));
      setClarifications([]);
      setAmbiguities([]);
      setRequirements(null);
      setDestinationResolution(null);
      if (result.reason === 'request-required') promptRef.current?.focus();
      return;
    }
    setError('');
    // The local parse is a recoverable preview/fallback; the single persisted first assistant turn performs semantic LLM extraction and clarification together.
    let interpreted = result.requirements;
    if (suggestedOrigin) interpreted = withApproximateDeviceOrigin(interpreted, suggestedOrigin, locale);
    interpreted = resolveRelativeTripDates(interpreted, deviceCalendarDate(travelerTimezone), travelerTimezone);
    if (interpreted.missingRequired.length || interpreted.ambiguousRequired.length || interpreted.clarificationFields?.length) {
      setRequirements(interpreted);
      loadDestinationResolution(interpreted.destinations.value, locale);
      setClarifications(interpreted.missingRequired);
      setAmbiguities(interpreted.ambiguousRequired);
      // Missing fields are a reason to clarify, not a reason to block the
      // authenticated assistant. Persist the original request and let the
      // first assistant turn ask for the missing information.
      if (!authSession || !online) return;
    } else {
      setClarifications([]);
      setAmbiguities([]);
    }
    setRequirements(interpreted);
    loadDestinationResolution(interpreted.destinations.value, locale);
  };

  const clearTripDraft = () => {
    catalogueRequestVersion.current += 1;
    if (promptRef.current) promptRef.current.value = '';
    requestTextRef.current = '';
    setError(''); setClarifications([]); setAmbiguities([]); setRequirements(null); setDestinationResolution(null); setCatalogueLoading(false);
  };
  const tripCopy = tripMessages[locale];
  const requirementCopy = requirementClarificationMessages[locale];

  if (window.location.pathname === '/admin/ai-providers' || window.location.pathname === '/admin/catalogue-review') {
    return <>
      <header className="topbar">
        <a className="brand" href="/"><span className="brand-mark" aria-hidden="true">Ø±</span><span>{t('brand')}<small>{t('tagline')}</small></span></a>
        <div className="top-actions">
          <ThemeSwitcher locale={locale} />
          <AuthPanel locale={locale} onSessionChange={setAuthSession} />
          <label className="sr-only" htmlFor="locale">{t('labelLanguage')}</label>
          <select id="locale" value={locale} onChange={event => setLocale(event.target.value as Locale)}>
            {(['fa-IR', 'en-US', 'ar'] as Locale[]).map(value => <option key={value} value={value}>{languageName[value]}</option>)}
          </select>
        </div>
      </header>
      {window.location.pathname === '/admin/catalogue-review'
        ? <CatalogueReviewPanel locale={locale} csrfToken={authSession?.csrf_token ?? ''} />
        : <AiProviderAdminPanel locale={locale} csrfToken={authSession?.csrf_token ?? ''}
        authMethod={authSession?.user.auth_method === 'staging_invite' ? undefined : authSession?.user.auth_method} />
      }
    </>;
  }

  return (
    <>
      <header className="topbar">
        <a className="brand" href="#home">
          <span className="brand-mark" aria-hidden="true">ر</span>
          <span>{t('brand')}<small>{t('tagline')}</small></span>
        </a>
        <nav aria-label={t('navExplore')}>
          <a href="#discover">{t('navExplore')}</a>
          <a href="#itinerary">{t('navPlan')}</a>
          {authSession && <a href="/partners">{locale === 'fa-IR' ? 'فضای کسب‌وکار' : locale === 'ar' ? 'مساحة الشركاء' : 'Partner workspace'}</a>}
          {authSession?.user.auth_method === 'local_owner' && <a href="/admin/catalogue-review">{locale === 'fa-IR' ? 'بازبینی کاتالوگ' : locale === 'ar' ? 'مراجعة الدليل' : 'Catalogue review'}</a>}
          {authSession?.user.auth_method === 'local_owner' && <a href="/admin/ai-providers">AI admin</a>}
        </nav>
        <div className="top-actions">
          <ThemeSwitcher locale={locale} />
          <AuthPanel locale={locale} onSessionChange={setAuthSession} />
          <label className="sr-only" htmlFor="locale">{t('labelLanguage')}</label>
          <select id="locale" value={locale} onChange={event => setLocale(event.target.value as Locale)}>
            {(['fa-IR', 'en-US', 'ar'] as Locale[]).map(value => (
              <option key={value} value={value}>{languageName[value]}</option>
            ))}
          </select>
        </div>
      </header>

      {!online && <p className="offline-banner" role="status">{t('offline')}</p>}

      {window.location.pathname === '/partners' ? (authSession
        ? <PartnerWorkspace locale={locale} csrfToken={authSession.csrf_token} />
        : <main className="partner-workspace"><h1>{locale === 'fa-IR' ? 'برای ادامه وارد شوید' : locale === 'ar' ? 'سجّل الدخول للمتابعة' : 'Sign in to continue'}</h1><AuthPanel locale={locale} onSessionChange={setAuthSession} /></main>) : <main id="home" className={authSession ? 'traveler-app' : undefined}>
        <div className={authSession ? 'unified-trip-experience' : undefined}>
        {(!authSession || !conversationVisible) && <section className={authSession ? 'hero hero-planner rahgard-chat-entrance' : 'hero'}>
          <div className="hero-copy">
            {authSession && <p className="rahgard-chat-status" role="status" data-provider-state={assistantRouteState}>
              <span aria-hidden="true">●</span> {assistantRouteState === 'connected'
                ? (locale === 'fa-IR' ? 'هوش مصنوعی متصل است' : locale === 'ar' ? 'الذكاء الاصطناعي متصل' : 'AI connected')
                : assistantRouteState === 'configured'
                  ? (locale === 'fa-IR' ? 'سرویس تنظیم شده؛ اتصال هنوز تأیید نشده' : 'AI configured; connectivity unverified')
                  : assistantRouteState === 'loading'
                    ? (locale === 'fa-IR' ? 'در حال بررسی اتصال هوش مصنوعی…' : 'Checking AI connection…')
                    : assistantRouteState === 'quota_exhausted'
                      ? (locale === 'fa-IR' ? 'سهمیهٔ دستیار پایان یافته است' : 'AI quota exhausted')
                      : (locale === 'fa-IR' ? 'دستیار در دسترس نیست؛ استخراج جایگزین فعال می‌شود' : 'AI unavailable; fallback available')}
            </p>}
            <p className="eyebrow"><span className="sun">✳</span>{t('heroEyebrow')}</p>
            <h1>{authSession ? plannerCopy[locale].title : t('heroTitle')}</h1>
            <p className="hero-body">{authSession ? plannerCopy[locale].intro : t('heroBody')}</p>
            {authSession && <div className="rahgard-chat-intro" aria-label={locale === 'fa-IR' ? 'شروع گفت‌وگوی سفر' : 'Start travel conversation'}>
              <div className="rahgard-chat-greeting">
                <strong>{locale === 'fa-IR' ? '✦ دستیار رهگارد' : locale === 'ar' ? '✦ مساعد رهگارد' : '✦ Rahgard assistant'}</strong>
                <p>{locale === 'fa-IR'
                  ? 'سلام! سفرتان را با زبان خودتان توضیح دهید. از شما سؤال می‌پرسم تا مقصد و مدت مشخص شود؛ سپس نیازها را برای بازبینی در کنار همین گفتگو نمایش می‌دهم.'
                  : locale === 'ar'
                    ? 'أهلاً! أخبرني عن رحلتك بطريقتك. سأطرح أسئلة عن الوجهة والمدة ثم نراجع التفاصيل معاً.'
                    : 'Welcome! Tell me about your trip in your own words. I will clarify the destination and duration, then we can review the details here.'}</p>
              </div>
            </div>}
            <details className="trip-intake-panel" open={!authSession || !conversationVisible}>
            <summary hidden={!authSession || !conversationVisible}>{tripCopy.requestLabel}</summary>
            <form className="trip-form" onSubmit={submit} noValidate>
              <label htmlFor="trip-prompt">{tripCopy.requestLabel}</label>
              <p className="trip-form-help" id="trip-prompt-help">{tripCopy.requestHelp}</p>
              <textarea
                ref={promptRef}
                id="trip-prompt"
                name="requestText"
                rows={4}
                maxLength={1200}
                defaultValue=""
                onKeyDown={event => {
                  if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
                onInput={event => { catalogueRequestVersion.current += 1; requestTextRef.current = event.currentTarget.value; setRequirements(null); setClarifications([]); setAmbiguities([]); setDestinationResolution(null); setCatalogueLoading(false); setError(''); }}
                placeholder={tripCopy.placeholder}
                aria-describedby={error ? 'form-error trip-prompt-help' : 'trip-prompt-help'}
                aria-invalid={error ? true : undefined}
              />
              {authSession && <aside className="ai-processing-notice">
                <strong>{locale === 'fa-IR' ? 'گفت‌وگوی هوشمند' : locale === 'ar' ? 'المحادثة الذكية' : 'AI conversation'}</strong>
                <p className="assistant-action-help">
                  {locale === 'fa-IR' ? 'گفت‌وگوی هوشمند به‌صورت پیش‌فرض فعال است؛ متن درخواست و پیام‌های سفر برای پاسخ به سرویس هوش مصنوعی تنظیم‌شده ارسال می‌شود. هنگام اختلال، تحلیل قواعدمحور در دسترس است.'
                    : locale === 'ar' ? 'المحادثة الذكية مفعّلة افتراضياً. تُرسل رسائل الرحلة إلى خدمة الذكاء الاصطناعي المهيأة، مع تحليل احتياطي عند تعذر الاتصال.'
                      : 'AI conversation is on by default. Trip messages are sent to the configured AI service; rule-based extraction is the fallback.'}
                </p>
                <p className="assistant-provider-state" role="status" data-provider-state={assistantRouteState}>
                  {assistantRouteState === 'loading' ? (locale === 'fa-IR' ? 'در حال بررسی وضعیت دستیار…' : locale === 'ar' ? 'جارٍ التحقق من حالة المساعد…' : 'Checking assistant status…')
                    : assistantRouteState === 'connected' ? (locale === 'fa-IR' ? 'اتصال به سرویس هوش مصنوعی برقرار است.' : locale === 'ar' ? 'تم الاتصال بخدمة الذكاء الاصطناعي.' : 'Connected to the AI service.')
                    : assistantRouteState === 'configured' ? (locale === 'fa-IR' ? 'مسیر دستیار تنظیم شده است؛ اتصال هنوز تأیید نشده.' : locale === 'ar' ? 'مسار المساعد مُعدّ؛ لم يُتحقق من الاتصال بعد.' : 'Assistant route configured. Connection has not been verified.')
                      : assistantRouteState === 'quota_exhausted' ? (locale === 'fa-IR' ? 'سهمیهٔ روزانهٔ دستیار تمام شده است.' : locale === 'ar' ? 'اكتملت الحصة اليومية للمساعد.' : 'The assistant daily limit is reached.')
                        : assistantRouteState === 'disabled' ? (locale === 'fa-IR' ? 'پاسخ‌گویی هوشمند فعال نیست؛ می‌توانید دستی برنامه‌ریزی کنید.' : locale === 'ar' ? 'المساعد غير مفعّل؛ يمكنك التخطيط يدوياً.' : 'AI replies are disabled; manual planning remains available.')
                          : (locale === 'fa-IR' ? 'وضعیت دستیار در دسترس نیست؛ درخواست سفر را می‌توانید ذخیره کنید.' : locale === 'ar' ? 'حالة المساعد غير متاحة؛ يمكنك حفظ طلب الرحلة.' : 'Assistant status is unavailable; you can still save the trip request.')}
                  {assistantRemaining !== null && assistantRouteState !== 'disabled' && assistantRouteState !== 'unavailable' && <> · {locale === 'fa-IR' ? `سهمیهٔ باقی‌مانده: ${formatNumber(locale, assistantRemaining)}` : locale === 'ar' ? `المتبقي اليوم: ${formatNumber(locale, assistantRemaining)}` : `${assistantRemaining} requests available today`}</>}
                </p>
              </aside>}
              {error && <p id="form-error" className="form-error" role="alert">{error}</p>}
              <button type="submit" className="primary">
                {authSession ? (locale === 'fa-IR' ? 'ارسال پیام و شروع گفت‌وگو' : locale === 'ar' ? 'أرسل الرسالة وابدأ المحادثة' : 'Send and start conversation') : tripCopy.submit}
                <span aria-hidden="true">↗</span>
              </button>
              <p className="fixture-pill">{tripCopy.sessionNotice}</p>
              {!!clarifications.length && requirements && (!authSession || assistantRouteState === 'disabled' || assistantRouteState === 'unavailable') && <section className="trip-response" aria-live="polite" aria-labelledby="clarification-title">
                <h2 id="clarification-title">{tripCopy.clarificationTitle}</h2>
                <ul>{clarifications.map(field => <li key={field}>{field === 'destination' ? tripCopy.askDestination : tripCopy.askDuration}</li>)}
                  {ambiguities.map(field => <li key={field}>{field === 'destination' ? tripCopy.askAmbiguousDestination : tripCopy.askAmbiguousDuration}</li>)}</ul>
                {requirements.clarificationFields?.includes('budget.currency') && <p>{requirementCopy.budgetCurrency}</p>}
                {requirements.clarificationFields?.includes('relative_start_date.anchor') && <p>{requirementCopy.relativeAnchor}</p>}
              </section>}
              {requirements && (!authSession || assistantRouteState === 'disabled' || assistantRouteState === 'unavailable') && <section className="trip-response trip-summary" aria-live="polite" aria-labelledby="captured-title">
                <div className="trip-summary-heading"><h2 id="captured-title">{tripCopy.capturedTitle}</h2>
                  <button className="text-button" type="button" onClick={clearTripDraft}>{tripCopy.clearDraft}</button></div>
                <p>{tripCopy.capturedLocal}</p>
                {catalogueLoading && <p className="destination-catalogue-loading" role="status">{destinationResolutionMessages[locale].loading}</p>}
                {destinationResolution && <section className="destination-resolution" data-resolution={destinationResolution.kind} aria-live="polite">
                  {destinationResolution.items.map((item, index) => {
                    const copy = destinationResolutionMessages[locale];
                    if (item.kind === 'catalogue-unavailable') return <p key={index}>{copy.unavailable} <bdi>{item.originalPhrase}</bdi></p>;
                    if (item.kind === 'catalogue-empty') return <p key={index}>{copy.empty} <bdi>{item.originalPhrase}</bdi></p>;
                    if (item.kind === 'not-found') return <p key={index}>{copy.notFound.replace('{phrase}', item.originalPhrase)}</p>;
                    if (item.kind === 'resolved') return <p key={index} dir="auto">{item.destination.canonicalName}</p>;
                    if (item.kind === 'confirmed') return <p key={index} dir="auto">{item.destination.canonicalName} · {copy.selected}</p>;
                    return <fieldset key={index} className="destination-choice">
                      <legend>{copy.ambiguous.replace('{phrase}', item.originalPhrase)}</legend>
                      {item.candidates.map(candidate => <label key={candidate.destinationId} dir="auto">
                        <input type="radio" name={`destination-choice-${index}`} value={candidate.destinationId}
                          checked={false}
                          onChange={() => setDestinationResolution(current => current ? confirmDestinationCandidate(current, index, candidate.destinationId) : current)} />
                        <span>{[candidate.localizedNames[locale] ?? candidate.canonicalName, candidate.cityName, candidate.provinceName].filter(Boolean).join(' · ')}</span>
                      </label>)}
                      <p>{copy.none}</p>
                    </fieldset>;
                  })}
                </section>}
                <dl>
                  <div><dt>{tripCopy.summaryDestination}</dt><dd dir="auto">{requirements.destinations.value?.join(' → ') ?? tripCopy.unknown}</dd></div>
                  <div className="trip-summary-request"><dt>{tripCopy.summaryRequest}</dt><dd dir="auto">{requirements.requestText}</dd></div>
                  <div><dt>{tripCopy.summaryDuration}</dt><dd>{requirements.durationDays.value === null ? tripCopy.unknown : tripCopy.durationDays.replace('{value}', formatNumber(locale, requirements.durationDays.value))}</dd></div>
                  <div><dt>{requirementCopy.relativeDeparture.split('{days}')[0].trim()}</dt><dd>{requirements.relativeStartDate.value ? requirementCopy.relativeDeparture.replace('{days}', formatNumber(locale, requirements.relativeStartDate.value.offset_days)) : tripCopy.unknown}</dd></div>
                  <div><dt>{tripCopy.summaryTravelers}</dt><dd>{requirements.travelerCount.value === null ? tripCopy.unknown : formatNumber(locale, requirements.travelerCount.value)}</dd></div>
                  <div><dt>{tripCopy.summaryBudget}</dt><dd dir="auto">{requirements.budget.value?.raw ?? tripCopy.unknown}</dd></div>
                  <div><dt>{tripCopy.summaryInterests}</dt><dd dir="auto">{requirements.interests.value?.map(value => displayTripInterest(value, locale)).join('، ') ?? tripCopy.unknown}</dd></div>
                  <div><dt>{tripCopy.summaryDates}</dt><dd dir="auto">{requirements.travelDates.value ? `${requirements.travelDates.value.start} – ${requirements.travelDates.value.end}` : tripCopy.unknown}</dd></div>
                  <div><dt>{tripCopy.summaryConstraints}</dt><dd dir="auto">{requirements.constraints.value?.join('، ') ?? tripCopy.unknown}</dd></div>
                </dl>
                {requirements.budget.value && <p className="trip-budget-scope" role="note">{plannerCopy[locale].budgetScope}</p>}
                {authSession && <a className="planner-next-link" href="#itinerary">{plannerCopy[locale].next} ↓</a>}
              </section>}
            </form>
            </details>
          </div>
          {authSession && <aside className="rahgard-chat-guide" aria-label={locale === 'fa-IR' ? 'راهنمای نیازهای سفر' : 'Trip requirements guide'}>
            <h2>{locale === 'fa-IR' ? 'نیازهای سفر' : locale === 'ar' ? 'متطلبات الرحلة' : 'Trip requirements'}</h2>
            <p>{locale === 'fa-IR' ? 'در طول گفتگو، نیازهای سفر استخراج می‌شوند. اطلاعات نهایی را می‌توانید در همین صفحه اصلاح و تأیید کنید.' : locale === 'ar' ? 'سنستخلص المتطلبات أثناء المحادثة، ثم يمكنك تعديلها وتأكيدها هنا.' : 'Requirements are collected in the chat, then you can review and edit them here.'}</p>
            <div className="rahgard-guide-group">
              <strong>{locale === 'fa-IR' ? 'حداقل اطلاعات برای شروع برنامه‌ریزی' : 'Required to begin planning'}</strong>
              <ul>
                <li><span>{locale === 'fa-IR' ? 'مقصد سفر' : 'Destination'}</span><b>{locale === 'fa-IR' ? 'ضروری' : 'Required'}</b></li>
                <li><span>{locale === 'fa-IR' ? 'مدت سفر' : 'Duration'}</span><b>{locale === 'fa-IR' ? 'ضروری' : 'Required'}</b></li>
              </ul>
            </div>
            <div className="rahgard-guide-group">
              <strong>{locale === 'fa-IR' ? 'برای پیشنهاد دقیق‌تر' : 'Helpful optional details'}</strong>
              <p>{locale === 'fa-IR'
                ? 'مبدأ، تاریخ، تعداد مسافران، بودجه، علایق، غذای محلی، سختی مسیر و آب‌وهوا را هم می‌توانید در گفتگو مشخص کنید.'
                : 'Origin, dates, travelers, budget, interests, local food, route difficulty and weather can be clarified in chat.'}</p>
              <small>{locale === 'fa-IR' ? 'محدودیت‌های ضروری باید جداگانه بررسی شوند؛ اطلاعات تأییدنشده به‌عنوان واقعیت اعلام نمی‌شود.' : 'Safety-critical constraints still require explicit review.'}</small>
            </div>
          </aside>}

          {!authSession && <figure className="hero-art">
            {heroImageFailed ? (
              <div className="image-fallback" role="img" aria-label={t('imageFallback')}>{t('imageFallback')}</div>
            ) : (
              <picture>
              <source type="image/avif" srcSet="/images/naghshe-jahan-640.avif 640w, /images/naghshe-jahan-960.avif 960w, /images/naghshe-jahan-1280.avif 1280w" sizes="(max-width: 900px) 100vw, 55vw" />
              <source type="image/webp" srcSet="/images/naghshe-jahan-640.webp 640w, /images/naghshe-jahan-960.webp 960w, /images/naghshe-jahan-1280.webp 1280w" sizes="(max-width: 900px) 100vw, 55vw" />
              <img
                className="hero-photo"
                src={photos.hero}
                alt={t('heroImageAlt')}
                width="1280"
                height="853"
                fetchPriority="high"
                decoding="async"
                onError={() => setHeroImageFailed(true)}
              />
              </picture>
            )}
            <div className="hero-photo-shade" aria-hidden="true" />
            <figcaption className="hero-photo-caption">
              <span>{t('heroLocation')}</span>
              <PhotoCredit source={photoSources.hero} author="Bernard Gagnon" label={t('photoCreditLabel')} />
            </figcaption>
          </figure>}
        </section>}

        <PwaUpdateNotice locale={locale} />
        <TravelerJourney
          locale={locale}
          session={authSession}
          online={online}
          requirements={requirements}
          autoStartConversation
          assistantConfigured={assistantRouteState === 'loading' ? null : assistantRouteState !== 'disabled' && assistantRouteState !== 'quota_exhausted'}
          travelerTimezone={travelerTimezone}
          suggestedOrigin={suggestedOrigin}
          onManualDateOverride={() => { manualDateOverrideRequestRef.current = requestTextRef.current; }}
          onConversationVisibilityChange={setConversationVisible}
          onSessionExpired={() => setAuthSession(null)}
          onRestoreRequest={(text, restored) => {
            manualDateOverrideRequestRef.current = text;
            requestTextRef.current = text;
            if (promptRef.current) promptRef.current.value = text;
            setRequirements(restored);
            setClarifications(restored.missingRequired);
            setAmbiguities(restored.ambiguousRequired);
            setDestinationResolution(null);
          }}
          onStartNewDraft={clearTripDraft}
        />
        </div>

        {!authSession && <section className="section discover" id="discover">
          <div className="section-heading">
            <div>
              <p className="eyebrow">{t('explore')}</p>
              <h2>{t('featured')}</h2>
              <p>{t('featuredSub')}</p>
            </div>
          </div>

          <div className="cards">
            <article className="place-card card-kashan">
              <figure className="card-image">
                <picture><source type="image/avif" srcSet="/images/fin-garden-640.avif 640w, /images/fin-garden-960.avif 960w, /images/fin-garden-1280.avif 1280w" sizes="(max-width: 720px) 100vw, 33vw" /><source type="image/webp" srcSet="/images/fin-garden-640.webp 640w, /images/fin-garden-960.webp 960w, /images/fin-garden-1280.webp 1280w" sizes="(max-width: 720px) 100vw, 33vw" /><img src={photos.kashan} alt={t('cardOneImageAlt')} width="1280" height="1230" loading="lazy" decoding="async" /></picture>
                <span className="image-stamp">01</span>
              </figure>
              <div className="card-copy">
                <span>{t('cardOneMeta')}</span>
                <h3>{t('cardOne')}</h3>
                <PhotoCredit source={photoSources.kashan} author="Amirpashaei" label={t('photoCreditLabel')} />
              </div>
            </article>

            <article className="place-card card-yazd">
              <figure className="card-image">
                <picture><source type="image/avif" srcSet="/images/yazd-windcatchers-640.avif 640w, /images/yazd-windcatchers-960.avif 960w, /images/yazd-windcatchers-1280.avif 1280w" sizes="(max-width: 720px) 100vw, 33vw" /><source type="image/webp" srcSet="/images/yazd-windcatchers-640.webp 640w, /images/yazd-windcatchers-960.webp 960w, /images/yazd-windcatchers-1280.webp 1280w" sizes="(max-width: 720px) 100vw, 33vw" /><img src={photos.yazd} alt={t('cardTwoImageAlt')} width="1280" height="738" loading="lazy" decoding="async" /></picture>
                <span className="image-stamp">02</span>
              </figure>
              <div className="card-copy">
                <span>{t('cardTwoMeta')}</span>
                <h3>{t('cardTwo')}</h3>
                <PhotoCredit source={photoSources.yazd} author="Ms96" label={t('photoCreditLabel')} />
              </div>
            </article>

            <article className="place-card card-qeshm">
              <figure className="card-image">
                <picture><source type="image/avif" srcSet="/images/qeshm-hara-640.avif 640w, /images/qeshm-hara-960.avif 960w, /images/qeshm-hara-1280.avif 1280w" sizes="(max-width: 720px) 100vw, 33vw" /><source type="image/webp" srcSet="/images/qeshm-hara-640.webp 640w, /images/qeshm-hara-960.webp 960w, /images/qeshm-hara-1280.webp 1280w" sizes="(max-width: 720px) 100vw, 33vw" /><img src={photos.qeshm} alt={t('cardThreeImageAlt')} width="1280" height="960" loading="lazy" decoding="async" /></picture>
                <span className="image-stamp">03</span>
              </figure>
              <div className="card-copy">
                <span>{t('cardThreeMeta')}</span>
                <h3>{t('cardThree')}</h3>
                <PhotoCredit source={photoSources.qeshm} author="ImanFakhri" label={t('photoCreditLabel')} />
              </div>
            </article>
          </div>
        </section>}

      </main>}

      <footer>
        <span>{t('brand')} · {t('footer')}</span>
        <span>fa · en · ar</span>
      </footer>
    </>
  );
}
