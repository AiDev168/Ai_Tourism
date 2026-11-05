import { useEffect, useRef, useState } from 'react';
import { formatDate, formatNumber, interfaceActions, statusPreview, type Locale } from '../i18n/messages';
import { tripMessages } from '../i18n/tripMessages';
import { createTripRequirements, type TripRequirements } from '../trip/tripIntake';
import { useLocale } from '../i18n/LocaleContext';

const languageName: Record<Locale, string> = { 'fa-IR': 'فارسی', 'en-US': 'English', ar: 'العربية' };

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
  const [query, setQuery] = useState('');
  const [destination, setDestination] = useState('');
  const [durationDays, setDurationDays] = useState('');
  const [requirements, setRequirements] = useState<TripRequirements | null>(null);
  const [clarifications, setClarifications] = useState<Array<'destination' | 'duration'>>([]);
  const [error, setError] = useState('');
  const [heroImageFailed, setHeroImageFailed] = useState(false);
  const [itineraryEditing, setItineraryEditing] = useState(false);
  const [itineraryNotes, setItineraryNotes] = useState(['', '', '']);
  const [online, setOnline] = useState(navigator.onLine);
  const promptRef = useRef<HTMLTextAreaElement>(null);
  const requestTextRef = useRef('');

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    // Read the live form controls at the submit boundary. React state remains
    // useful for rendering, but it must not be the only source of submitted
    // text: FormData captures the exact values currently visible to the user.
    const formData = new FormData(event.currentTarget);
    const requestText = promptRef.current?.value ?? String(formData.get('requestText') ?? requestTextRef.current);
    const currentDestination = String(formData.get('destination') ?? '');
    const currentDurationDays = String(formData.get('durationDays') ?? '');
    setQuery(requestText);
    setDestination(currentDestination);
    setDurationDays(currentDurationDays);

    const result = createTripRequirements({
      requestText,
      destination: currentDestination,
      durationDays: currentDurationDays,
    });
    if (result.kind === 'invalid') {
      const messageKey = {
        'request-required': 'requestRequired',
        'request-too-long': 'requestTooLong',
        'destination-too-long': 'destinationTooLong',
        'duration-invalid': 'durationInvalid',
      } as const;
      setError(tripMessages[locale][messageKey[result.reason]]);
      setClarifications([]);
      setRequirements(null);
      if (result.reason === 'request-required') promptRef.current?.focus();
      return;
    }
    setError('');
    if (result.kind === 'clarification') {
      setRequirements(null);
      setClarifications(result.missing);
      return;
    }
    setClarifications([]);
    setRequirements(result.requirements);
  };

  const clearTripDraft = () => {
    setQuery(''); setDestination(''); setDurationDays(''); setError('');
    setClarifications([]); setRequirements(null);
  };
  const tripCopy = tripMessages[locale];

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
        </nav>
        <div className="top-actions">
          <label className="sr-only" htmlFor="locale">{t('labelLanguage')}</label>
          <select id="locale" value={locale} onChange={event => setLocale(event.target.value as Locale)}>
            {(['fa-IR', 'en-US', 'ar'] as Locale[]).map(value => (
              <option key={value} value={value}>{languageName[value]}</option>
            ))}
          </select>
        </div>
      </header>

      {!online && <p className="offline-banner" role="status">{t('offline')}</p>}

      <main id="home">
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow"><span className="sun">✳</span>{t('heroEyebrow')}</p>
            <h1>{t('heroTitle').split('\n').map((line, index) => <span key={index}>{line}<br /></span>)}</h1>
            <p className="hero-body">{t('heroBody')}</p>
            <form className="trip-form" onSubmit={submit} noValidate>
              <label htmlFor="trip-prompt">{t('promptLabel')}</label>
              <textarea
                ref={promptRef}
                id="trip-prompt"
                name="requestText"
                rows={2}
                maxLength={1200}
                value={query}
                onInput={event => { requestTextRef.current = event.currentTarget.value; }}
                onChange={event => { requestTextRef.current = event.currentTarget.value; setQuery(event.currentTarget.value); setRequirements(null); setClarifications([]); setError(''); }}
                placeholder={t('promptPlaceholder')}
                aria-describedby={error ? 'form-error' : undefined}
                aria-invalid={error ? true : undefined}
              />
              <div className="trip-fields">
                <div>
                  <label htmlFor="trip-destination">{tripCopy.destinationLabel}</label>
                  <input id="trip-destination" name="destination" autoComplete="off" maxLength={120} value={destination}
                    onChange={event => { setDestination(event.target.value); setRequirements(null); setClarifications([]); setError(''); }}
                    placeholder={tripCopy.destinationPlaceholder} />
                </div>
                <div>
                  <label htmlFor="trip-duration">{tripCopy.durationLabel}</label>
                  <select id="trip-duration" name="durationDays" value={durationDays}
                    onChange={event => { setDurationDays(event.target.value); setRequirements(null); setClarifications([]); setError(''); }}>
                    <option value="">{tripCopy.durationOptional}</option>
                    {[1, 2, 3].map(days => <option key={days} value={days}>{tripCopy.durationDays.replace('{value}', formatNumber(locale, days))}</option>)}
                  </select>
                </div>
              </div>
              {error && <p id="form-error" className="form-error" role="alert">{error}</p>}
              <button type="submit" className="primary">
                {t('startPlanning')} <span aria-hidden="true">↗</span>
              </button>
              <p className="fixture-pill">{tripCopy.sessionNotice}</p>
              {!!clarifications.length && <section className="trip-response" aria-live="polite" aria-labelledby="clarification-title">
                <h2 id="clarification-title">{tripCopy.clarificationTitle}</h2>
                <ul>{clarifications.map(field => <li key={field}>{field === 'destination' ? tripCopy.askDestination : tripCopy.askDuration}</li>)}</ul>
              </section>}
              {requirements && <section className="trip-response trip-summary" aria-live="polite" aria-labelledby="captured-title">
                <div className="trip-summary-heading"><h2 id="captured-title">{tripCopy.capturedTitle}</h2>
                  <button className="text-button" type="button" onClick={clearTripDraft}>{tripCopy.clearDraft}</button></div>
                <p>{tripCopy.capturedLocal}</p>
                <dl>
                  <div><dt>{tripCopy.summaryDestination}</dt><dd dir="auto">{requirements.destination}</dd></div>
                  <div><dt>{tripCopy.summaryDuration}</dt><dd>{tripCopy.durationDays.replace('{value}', formatNumber(locale, requirements.durationDays))}</dd></div>
                </dl>
              </section>}
            </form>
          </div>

          <figure className="hero-art">
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
          </figure>
        </section>

        <section className="section discover" id="discover">
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
        </section>

        <section className="journey-grid">
          <article className="conversation-panel">
            <div className="panel-title">
              <span className="mini-icon">✳</span>
              <span>{t('conversation')}</span>
              <span className="fixture-tag">UI</span>
            </div>
            <h2>{t('conversationTitle')}</h2>
            <div className="chat-bubble">
              <span className="assistant-avatar">ر</span>
              <div><small>{t('assistant')}</small><p>{t('assistantText')}</p></div>
            </div>
            <small className="fixture-note">{t('sample')}</small>
            <details className="state-preview">
              <summary>{statusPreview[locale]}</summary>
              <p role="status">{t('loading')}</p>
              <p role="alert">{t('error')}</p>
              <small>{t('sample')}</small>
            </details>
          </article>

          <article className="recommend-panel">
            <div className="panel-title">
              <span className="mini-icon">↗</span>
              {t('recommendations')}
              <span className="fixture-tag">UI</span>
            </div>
            <h2>{t('recommendationsTitle')}</h2>
            <div className="empty-state">
              <span>✳</span>
              <strong>{t('emptyTitle')}</strong>
              <p>{t('emptyBody')}</p>
            </div>
          </article>
        </section>

        <section className="itinerary" id="itinerary">
          <div className="itinerary-header">
            <div>
              <p className="eyebrow">{t('itinerary')}</p>
              <h2>{t('itineraryTitle')}</h2>
            </div>
            <span className="fixture-tag">UI</span>
            <button
              className="outline"
              type="button"
              onClick={() => setItineraryEditing(value => !value)}
              aria-pressed={itineraryEditing}
            >
              {itineraryEditing ? interfaceActions[locale].finishEdit : t('itineraryEdit')} <span>↗</span>
            </button>
          </div>
          <div className="day-strip">
            {[1, 2, 3].map(day => (
              <div className="day-card" key={day}>
                <div className="day-num">
                  <span>{t('day')}</span>
                  <b>{formatNumber(locale, day).padStart(2, '0')}</b>
                </div>
                <div>
                  <strong>{day === 1 ? t('morning') : day === 2 ? t('afternoon') : t('evening')}</strong>
                  {itineraryEditing ? (
                    <input
                      className="itinerary-input"
                      aria-label={t('day') + ' ' + formatNumber(locale, day)}
                      value={itineraryNotes[day - 1]}
                      onChange={event => setItineraryNotes(notes => notes.map((note, index) => index === day - 1 ? event.target.value : note))}
                      placeholder={t('sample')}
                    />
                  ) : <p>{itineraryNotes[day - 1] || t('sample')}</p>}
                </div>
                <span className="day-dot">✳</span>
              </div>
            ))}
          </div>
          <p className="warning">ⓘ {t('warning')}</p>
          <div className="locale-proof">
            <span>{formatDate(locale, new Date('2026-11-05T12:00:00Z'))}</span>
          </div>
        </section>
      </main>

      <footer>
        <span>{t('brand')} · {t('footer')}</span>
        <span>fa · en · ar</span>
      </footer>
    </>
  );
}
