import type { Locale } from '../i18n/messages';
import './TravelerGuidance.css';

type GuidedProgressProps = {
  locale: Locale;
  hasTrip: boolean;
  confirmed: boolean;
  hasRecommendations: boolean;
  hasItinerary: boolean;
};

const copy: Record<Locale, {
  heading: string; description: string; steps: readonly string[];
  next: readonly string[]; action: string; pending: string; done: string;
}> = {
  'fa-IR': {
    heading: 'مسیر برنامه‌ریزی سفر شما',
    description: 'از گفت‌وگو و شناخت نیازها تا پیشنهادهای مستند و برنامهٔ قابل‌ویرایش. هر مرحله با تأیید خودتان پیش می‌رود.',
    steps: ['شرح سفر', 'گفت‌وگو با مشاور', 'تأیید نیازها', 'پیشنهادهای مستند', 'برنامهٔ سفر'],
    next: ['سفر دلخواهتان را در کادر بالا شرح دهید.', 'پرسش‌های تکمیلی را در گفت‌وگو مطرح کنید و پاسخ دهید.',
      'مقصد، مدت، نیازهای ضروری و رضایت‌ها را مرور و تأیید کنید.',
      'پیشنهادها فقط با دادهٔ منتشرشده و معتبر نمایش داده می‌شوند.',
      'از مقصدهای واجد شرایط برنامه بسازید و آن را ذخیره کنید.'],
    action: 'ادامهٔ این مرحله', pending: 'در انتظار', done: 'انجام شد',
  },
  'en-US': {
    heading: 'Your trip planning journey',
    description: 'From conversation and requirements to sourced suggestions and an editable itinerary. You approve every important step.',
    steps: ['Describe trip', 'Talk to advisor', 'Review requirements', 'Verified suggestions', 'Travel plan'],
    next: ['Describe your ideal trip above.', 'Ask and answer follow-up questions in your conversation.',
      'Review and confirm your destination, duration, essential needs, and consent choices.',
      'Only destinations backed by published, approved data can appear.',
      'Create, edit, and save a plan from eligible destinations.'],
    action: 'Continue this step', pending: 'Pending', done: 'Completed',
  },
  ar: {
    heading: 'مراحل التخطيط لرحلتك',
    description: 'من المحادثة وفهم احتياجاتك إلى اقتراحات موثقة وخطة قابلة للتعديل. لا يتم التأكيد إلا باختيارك.',
    steps: ['صف الرحلة', 'تحدث مع المستشار', 'راجع الاحتياجات', 'اقتراحات موثقة', 'خطة الرحلة'],
    next: ['صف رحلتك المفضلة في الحقل أعلاه.', 'اسأل وأجب عن الأسئلة التوضيحية في المحادثة.',
      'راجع الوجهة والمدة والاحتياجات الأساسية وخيارات الموافقة.',
      'تظهر الوجهات المنشورة والمراجعة والمسنودة بمصادر فقط.',
      'أنشئ وعدّل واحفظ خطتك من الوجهات المؤهلة.'],
    action: 'متابعة هذه المرحلة', pending: 'بانتظار', done: 'اكتمل',
  },
};

export function TravelerGuidance({ locale, hasTrip, confirmed, hasRecommendations, hasItinerary }: GuidedProgressProps) {
  const t = copy[locale];
  const stage = !hasTrip ? 0 : !confirmed ? 1 : !hasRecommendations ? 3 : !hasItinerary ? 4 : 5;
  const current = Math.min(stage, 4);
  const target = !hasTrip ? 'trip-prompt' : !confirmed ? 'trip-follow-up'
    : !hasRecommendations ? 'journey-recommendations' : !hasItinerary ? 'journey-recommendations' : 'saved-itinerary-title';
  const navigate = () => {
    const element = document.getElementById(target);
    element?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) element.focus({ preventScroll: true });
  };
  return <section className="rahgard-progress" aria-label={t.heading}>
    <div className="rahgard-progress-header">
      <div><p className="eyebrow">RAHGARD</p><h3>{t.heading}</h3><p>{t.description}</p></div>
      <span className="rahgard-progress-count" aria-label={`${Math.min(stage, 5)} / 5`}>
        {Math.min(stage, 5)} / 5
      </span>
    </div>
    <ol className="rahgard-progress-steps">
      {t.steps.map((title, index) => <li key={title} className={index < stage ? 'is-complete' : index === current ? 'is-current' : 'is-pending'}
        aria-current={index === current && stage < 5 ? 'step' : undefined}>
        <span className="rahgard-progress-index" aria-hidden="true">{index < stage ? '✓' : index + 1}</span>
        <span>{title}</span>
      </li>)}
    </ol>
    <div className="rahgard-progress-next" role="status">
      <span>{stage >= 5 ? t.done : t.pending}: {t.next[current]}</span>
      {stage < 5 && <button type="button" onClick={navigate}>{t.action}</button>}
    </div>
  </section>;
}
