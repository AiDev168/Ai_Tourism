import type { Locale } from '../i18n/messages';

export type MissingTripField = 'destination' | 'duration';
export type GuidedQuestion = {
  field: MissingTripField;
  question: string;
  instruction: string;
  answerLabel: string;
};

const prompts: Record<Locale, Record<MissingTripField, GuidedQuestion>> = {
  'fa-IR': {
    destination: {
      field: 'destination',
      question: 'دوست دارید به کدام شهر یا مقصد سفر کنید؟',
      instruction: 'مثلاً «کاشان» را در گفت‌وگو بنویسید و «افزودن به گفت‌وگو» را بزنید. این نام هنوز تأیید نشده است.',
      answerLabel: 'پاسخ به سؤال مقصد',
    },
    duration: {
      field: 'duration',
      question: 'برای این سفر چند روز فرصت دارید؟',
      instruction: 'مثلاً «۵ روز» بنویسید و «افزودن به گفت‌وگو» را بزنید.',
      answerLabel: 'پاسخ به سؤال مدت سفر',
    },
  },
  'en-US': {
    destination: {
      field: 'destination',
      question: 'Which city or destination would you like to visit?',
      instruction: 'For example, enter “Shiraz” in the conversation and select “Add to conversation”. The city is not verified yet.',
      answerLabel: 'Answer destination question',
    },
    duration: {
      field: 'duration',
      question: 'How many days do you have for this trip?',
      instruction: 'For example, enter “5 days” and select “Add to conversation”.',
      answerLabel: 'Answer duration question',
    },
  },
  ar: {
    destination: {
      field: 'destination',
      question: 'إلى أي مدينة أو وجهة ترغب في السفر؟',
      instruction: 'مثلاً اكتب «أصفهان» في المحادثة واختر «إضافة إلى المحادثة». لم يتم التحقق من الوجهة بعد.',
      answerLabel: 'الإجابة عن سؤال الوجهة',
    },
    duration: {
      field: 'duration',
      question: 'كم يوماً لديك لهذه الرحلة؟',
      instruction: 'مثلاً اكتب «5 أيام» واختر «إضافة إلى المحادثة».',
      answerLabel: 'الإجابة عن سؤال مدة الرحلة',
    },
  },
};

export function nextTripQuestion(
  locale: Locale, destinations: readonly string[], durationText: string,
): GuidedQuestion | null {
  if (!destinations.some(name => name.trim())) return prompts[locale].destination;
  const count = Number(durationText);
  if (!durationText.trim() || !Number.isInteger(count) || count < 1 || count > 365) {
    return prompts[locale].duration;
  }
  return null;
}
