import { useEffect, useRef, useState } from 'react';
import { formatNumber, type Locale } from '../i18n/messages';
import { tripMessages } from '../i18n/tripMessages';
import { requirementClarificationMessages } from '../i18n/requirementClarificationMessages';
import { destinationResolutionMessages } from '../i18n/destinationResolutionMessages';
import { createTripRequirements, MAX_TRIP_DURATION_DAYS, tripRequirementsV1ToTripRequirements, type TripRequirements } from '../trip/tripIntake';
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

const destinationCatalog = new ApiDestinationCatalogPort();

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

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    // Read the live form controls at the submit boundary. React state remains
    // useful for rendering, but it must not be the only source of submitted
    // text: FormData captures the exact values currently visible to the user.
    const formData = new FormData(event.currentTarget);
    const requestText = promptRef.current?.value ?? String(formData.get('requestText') ?? requestTextRef.current);
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
    let interpreted = result.requirements;
    if (authSession && online) {
      try {
        const response = await travelerApi.interpretRequirements(authSession.csrf_token, {
          request_text: requestText, locale,
        });
        interpreted = tripRequirementsV1ToTripRequirements(response.requirements);
      } catch {
        setError(locale === 'fa-IR' ? 'برداشت نیازهای سفر در سرور انجام نشد. دوباره تلاش کنید.'
          : locale === 'ar' ? 'تعذر تحليل متطلبات الرحلة على الخادم. حاول مرة أخرى.'
            : 'The server could not interpret this trip request. Please try again.');
        return;
      }
    }
    if (result.kind === 'clarification' || interpreted.clarificationFields?.length) {
      setRequirements(interpreted);
      loadDestinationResolution(interpreted.destinations.value, locale);
      setClarifications(interpreted.missingRequired);
      setAmbiguities(interpreted.ambiguousRequired);
      return;
    }
    setClarifications([]);
    setAmbiguities([]);
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

  if (window.location.pathname === '/admin/ai-providers') {
    return <>
      <header className="topbar">
        <a className="brand" href="/"><span className="brand-mark" aria-hidden="true">Ø±</span><span>{t('brand')}<small>{t('tagline')}</small></span></a>
        <div className="top-actions">
          <AuthPanel locale={locale} onSessionChange={setAuthSession} />
          <label className="sr-only" htmlFor="locale">{t('labelLanguage')}</label>
          <select id="locale" value={locale} onChange={event => setLocale(event.target.value as Locale)}>
            {(['fa-IR', 'en-US', 'ar'] as Locale[]).map(value => <option key={value} value={value}>{languageName[value]}</option>)}
          </select>
        </div>
      </header>
      <AiProviderAdminPanel locale={locale} csrfToken={authSession?.csrf_token ?? ''}
        authMethod={authSession?.user.auth_method} />
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
          {authSession?.user.auth_method === 'local_owner' && <a href="/admin/ai-providers">AI admin</a>}
        </nav>
        <div className="top-actions">
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

      <main id="home" className={authSession ? 'traveler-app' : undefined}>
        <section className={authSession ? 'hero hero-planner' : 'hero'}>
          <div className="hero-copy">
            <p className="eyebrow"><span className="sun">✳</span>{t('heroEyebrow')}</p>
            <h1>{authSession ? plannerCopy[locale].title : t('heroTitle').split('\n').map((line, index) => <span key={index}>{line}<br /></span>)}</h1>
            <p className="hero-body">{authSession ? plannerCopy[locale].intro : t('heroBody')}</p>
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
                onInput={event => { catalogueRequestVersion.current += 1; requestTextRef.current = event.currentTarget.value; setRequirements(null); setClarifications([]); setAmbiguities([]); setDestinationResolution(null); setCatalogueLoading(false); setError(''); }}
                placeholder={tripCopy.placeholder}
                aria-describedby={error ? 'form-error trip-prompt-help' : 'trip-prompt-help'}
                aria-invalid={error ? true : undefined}
              />
              {error && <p id="form-error" className="form-error" role="alert">{error}</p>}
              <button type="submit" className="primary">
                {tripCopy.submit} <span aria-hidden="true">↗</span>
              </button>
              <p className="fixture-pill">{tripCopy.sessionNotice}</p>
              {!!clarifications.length && requirements && <section className="trip-response" aria-live="polite" aria-labelledby="clarification-title">
                <h2 id="clarification-title">{tripCopy.clarificationTitle}</h2>
                <ul>{clarifications.map(field => <li key={field}>{field === 'destination' ? tripCopy.askDestination : tripCopy.askDuration}</li>)}
                  {ambiguities.map(field => <li key={field}>{field === 'destination' ? tripCopy.askAmbiguousDestination : tripCopy.askAmbiguousDuration}</li>)}</ul>
                {requirements.clarificationFields?.includes('budget.currency') && <p>{requirementCopy.budgetCurrency}</p>}
                {requirements.clarificationFields?.includes('relative_start_date.anchor') && <p>{requirementCopy.relativeAnchor}</p>}
              </section>}
              {requirements && <section className="trip-response trip-summary" aria-live="polite" aria-labelledby="captured-title">
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
          </div>

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
        </section>

        <PwaUpdateNotice locale={locale} />
        <TravelerJourney
          locale={locale}
          session={authSession}
          online={online}
          requirements={requirements}
          onSessionExpired={() => setAuthSession(null)}
          onRestoreRequest={(text, restored) => {
            requestTextRef.current = text;
            if (promptRef.current) promptRef.current.value = text;
            setRequirements(restored);
            setClarifications(restored.missingRequired);
            setAmbiguities(restored.ambiguousRequired);
            setDestinationResolution(null);
          }}
          onStartNewDraft={clearTripDraft}
        />

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

      </main>

      <footer>
        <span>{t('brand')} · {t('footer')}</span>
        <span>fa · en · ar</span>
      </footer>
    </>
  );
}
