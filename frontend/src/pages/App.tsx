import { useEffect, useState } from 'react';
import { formatDate, formatNumber, interfaceActions, statusPreview, type Locale } from '../i18n/messages';
import { useLocale } from '../i18n/LocaleContext';

const languageName: Record<Locale, string> = { 'fa-IR': 'فارسی', 'en-US': 'English', ar: 'العربية' };

const photos = {
  hero: 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Naqsh-e_Jahan_Square%2C_Isfahan_02.jpg/1280px-Naqsh-e_Jahan_Square%2C_Isfahan_02.jpg',
  kashan: 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/Fin_Garden%2C_Kashan%2C_Iran.jpg/1280px-Fin_Garden%2C_Kashan%2C_Iran.jpg',
  yazd: 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/Windcatchers_in_Yazd.jpg/1280px-Windcatchers_in_Yazd.jpg',
  qeshm: 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/81/Hara_forests_of_Qeshm_-_1.jpg/1280px-Hara_forests_of_Qeshm_-_1.jpg'
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
  const [error, setError] = useState('');
  const [sent, setSent] = useState(false);
  const [heroImageFailed, setHeroImageFailed] = useState(false);
  const [itineraryEditing, setItineraryEditing] = useState(false);
  const [itineraryNotes, setItineraryNotes] = useState(['', '', '']);
  const [online, setOnline] = useState(navigator.onLine);

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!query.trim()) {
      setError(t('formRequired'));
      return;
    }
    setError('');
    setSent(true);
  };

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
                id="trip-prompt"
                rows={2}
                value={query}
                onChange={event => setQuery(event.target.value)}
                placeholder={t('promptPlaceholder')}
                aria-describedby={error ? 'form-error' : undefined}
              />
              {error && <p id="form-error" className="form-error" role="alert">{error}</p>}
              <button type="submit" className="primary">
                {t('startPlanning')} <span aria-hidden="true">↗</span>
              </button>
              {sent && <p className="notice" role="status">{t('noApi')}</p>}
              <p className="fixture-pill">{t('noApi')}</p>
            </form>
          </div>

          <figure className="hero-art">
            {heroImageFailed ? (
              <div className="image-fallback" role="img" aria-label={t('imageFallback')}>{t('imageFallback')}</div>
            ) : (
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
            <a href="#discover" className="text-link">{t('seeAll')} <span>↗</span></a>
          </div>

          <div className="cards">
            <article className="place-card card-kashan">
              <figure className="card-image">
                <img src={photos.kashan} alt={t('cardOneImageAlt')} width="1280" height="1230" loading="lazy" decoding="async" />
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
                <img src={photos.yazd} alt={t('cardTwoImageAlt')} width="1280" height="738" loading="lazy" decoding="async" />
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
                <img src={photos.qeshm} alt={t('cardThreeImageAlt')} width="1280" height="960" loading="lazy" decoding="async" />
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
            <div className="chat-input"><span>{t('yourMessage')}</span><button aria-label={t('send')}>↑</button></div>
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
