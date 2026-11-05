import { useEffect, useState } from 'react';
import { formatDate, formatNumber, interfaceActions, statusPreview, type Locale } from '../i18n/messages';
import { useLocale } from '../i18n/LocaleContext';

const languageName: Record<Locale, string> = { 'fa-IR': 'فارسی', 'en-US': 'English', ar: 'العربية' };
export function App() {
  const { locale, setLocale, t } = useLocale();
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [sent, setSent] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);
  const [itineraryEditing, setItineraryEditing] = useState(false);
  const [itineraryNotes, setItineraryNotes] = useState(['', '', '']);
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => { const update = () => setOnline(navigator.onLine); window.addEventListener('online', update); window.addEventListener('offline', update); return () => { window.removeEventListener('online', update); window.removeEventListener('offline', update); }; }, []);
  const submit = (event: React.FormEvent) => { event.preventDefault(); if (!query.trim()) { setError(t('formRequired')); return; } setError(''); setSent(true); };
  return <>
    <header className="topbar"><a className="brand" href="#home"><span className="brand-mark" aria-hidden="true">ر</span><span>{t('brand')}<small>{t('tagline')}</small></span></a>
      <nav aria-label={t('navExplore')}><a href="#discover">{t('navExplore')}</a><a href="#itinerary">{t('navPlan')}</a></nav>
      <div className="top-actions"><label className="sr-only" htmlFor="locale">{t('labelLanguage')}</label><select id="locale" value={locale} onChange={e => setLocale(e.target.value as Locale)}>{(['fa-IR','en-US','ar'] as Locale[]).map(x => <option key={x} value={x}>{languageName[x]}</option>)}</select></div>
    </header>
    {!online && <p className="offline-banner" role="status">{t('offline')}</p>}
    <main id="home">
      <section className="hero"><div className="hero-copy"><p className="eyebrow"><span className="sun">✳</span>{t('heroEyebrow')}</p><h1>{t('heroTitle').split('\n').map((line,i)=><span key={i}>{line}<br/></span>)}</h1><p className="hero-body">{t('heroBody')}</p><form className="trip-form" onSubmit={submit} noValidate><label htmlFor="trip-prompt">{t('promptLabel')}</label><textarea id="trip-prompt" rows={2} value={query} onChange={e=>setQuery(e.target.value)} placeholder={t('promptPlaceholder')} aria-describedby={error ? 'form-error' : undefined}/>{error&&<p id="form-error" className="form-error" role="alert">{error}</p>}<button type="submit" className="primary">{t('startPlanning')} <span aria-hidden="true">↗</span></button>{sent&&<p className="notice" role="status">{t('noApi')}</p>}<p className="fixture-pill">{t('noApi')}</p></form></div>
        <div className="hero-art">{imageFailed ? <div className="image-fallback" role="img" aria-label={t('imageFallback')}>{t('imageFallback')}</div> : <img className="hero-photo" src="/hero-plateau.webp" alt={t('heroImageAlt')} fetchPriority="high" onError={() => setImageFailed(true)}/>}</div>
      </section>
      <section className="section discover" id="discover"><div className="section-heading"><div><p className="eyebrow">{t('explore')}</p><h2>{t('featured')}</h2><p>{t('featuredSub')}</p></div><a href="#discover" className="text-link">{t('seeAll')} <span>↗</span></a></div>
        <div className="cards"><article className="place-card card-kashan"><div className="card-image"><span className="image-stamp">01</span><div className="arch arch-one"/><div className="arch arch-two"/><div className="card-plant">✳</div></div><div className="card-copy"><span>{t('cardOneMeta')}</span><h3>{t('cardOne')}</h3></div></article><article className="place-card card-yazd"><div className="card-image"><span className="image-stamp">02</span><div className="dome"/><div className="tower"/><div className="tiny-sun"/></div><div className="card-copy"><span>{t('cardTwoMeta')}</span><h3>{t('cardTwo')}</h3></div></article><article className="place-card card-qeshm"><div className="card-image"><span className="image-stamp">03</span><div className="sea-cliff"/><div className="sea-wave"/></div><div className="card-copy"><span>{t('cardThreeMeta')}</span><h3>{t('cardThree')}</h3></div></article></div>
      </section>
      <section className="journey-grid"><article className="conversation-panel"><div className="panel-title"><span className="mini-icon">✳</span><span>{t('conversation')}</span><span className="fixture-tag">UI</span></div><h2>{t('conversationTitle')}</h2><div className="chat-bubble"><span className="assistant-avatar">ر</span><div><small>{t('assistant')}</small><p>{t('assistantText')}</p></div></div><div className="chat-input"><span>{t('yourMessage')}</span><button aria-label={t('send')}>↑</button></div><small className="fixture-note">{t('sample')}</small><details className="state-preview"><summary>{statusPreview[locale]}</summary><p role="status">{t('loading')}</p><p role="alert">{t('error')}</p><small>{t('sample')}</small></details></article>
        <article className="recommend-panel"><div className="panel-title"><span className="mini-icon">↗</span>{t('recommendations')}<span className="fixture-tag">UI</span></div><h2>{t('recommendationsTitle')}</h2><div className="empty-state"><span>✳</span><strong>{t('emptyTitle')}</strong><p>{t('emptyBody')}</p></div></article>
      </section>
      <section className="itinerary" id="itinerary"><div className="itinerary-header"><div><p className="eyebrow">{t('itinerary')}</p><h2>{t('itineraryTitle')}</h2></div><button className="outline" type="button" onClick={() => setItineraryEditing(value => !value)} aria-pressed={itineraryEditing}>{itineraryEditing ? interfaceActions[locale].finishEdit : t('itineraryEdit')} <span>↗</span></button></div><div className="day-strip">{[1,2,3].map(n=><div className="day-card" key={n}><div className="day-num"><span>{t('day')}</span><b>{formatNumber(locale,n).padStart(2,'0')}</b></div><div><strong>{n===1?t('morning'):n===2?t('afternoon'):t('evening')}</strong>{itineraryEditing ? <input className="itinerary-input" aria-label={`${t('day')} ${formatNumber(locale,n)}`} value={itineraryNotes[n-1]} onChange={event => setItineraryNotes(notes => notes.map((note,index) => index === n-1 ? event.target.value : note))} placeholder={t('sample')}/> : <p>{itineraryNotes[n-1] || t('sample')}</p>}</div><span className="day-dot">✳</span></div>)}</div><p className="warning">ⓘ {t('warning')}</p><div className="locale-proof"><span>{formatDate(locale,new Date('2026-11-05T12:00:00Z'))}</span></div></section>
    </main>
    <footer><span>{t('brand')} · {t('footer')}</span><span>fa · en · ar</span></footer>
  </>;
}
