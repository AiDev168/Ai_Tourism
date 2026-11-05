import type { Locale } from './messages';

export const tripMessages = {
  'fa-IR': {
    destinationLabel: 'مقصدی که در نظر داری', destinationPlaceholder: 'نام شهر یا منطقه',
    durationLabel: 'مدت سفر', durationOptional: 'هنوز مشخص نیست', durationDays: '{value} روز',
    sessionNotice: 'پیش‌نویس فقط در همین صفحه نگه داشته می‌شود؛ ارسال یا ذخیره نمی‌شود.',
    clarificationTitle: 'برای ساختن پیش‌نویس، این موارد را روشن کن:', askDestination: 'کدام شهر یا منطقه را در نظر داری؟', askDuration: 'سفر چند روزه است؟ (۱ تا ۳ روز)',
    capturedTitle: 'نیازهای سفرت ثبت شد', capturedLocal: 'این یک پیش‌نویس موقت در همین نشست است؛ هنوز مقصد یا اطلاعات سفر تأیید نشده‌اند.',
    summaryDestination: 'مقصد واردشده', summaryDuration: 'مدت درخواستی', clearDraft: 'پاک‌کردن پیش‌نویس',
    requestRequired: 'شرح سفر باید دست‌کم ۵ نویسه داشته باشد.', requestTooLong: 'شرح سفر بیش از حد طولانی است؛ حداکثر ۱۲۰۰ نویسه مجاز است.', destinationTooLong: 'نام مقصد حداکثر می‌تواند ۱۲۰ نویسه باشد.', durationInvalid: 'مدت سفر باید از ۱ تا ۳ روز باشد.',
    daysInvalid: 'مدت سفر باید از ۱ تا ۳ روز باشد.', durationDetected: 'مدت سفر از متن درخواست تشخیص داده شد.',
    fixtureLabel: 'تصویر نمایشی · مقصد تأییدشده یا پیشنهاد واقعی نیست',
  },
  'en-US': {
    destinationLabel: 'Destination you have in mind', destinationPlaceholder: 'City or region name',
    durationLabel: 'Trip length', durationOptional: 'Not sure yet', durationDays: '{value} days',
    sessionNotice: 'This draft stays on this page only. It is not sent or saved.',
    clarificationTitle: 'A couple of details will help shape your draft:', askDestination: 'Which city or region are you considering?', askDuration: 'How long is the trip? (1 to 3 days)',
    capturedTitle: 'Trip requirements captured', capturedLocal: 'This is a temporary draft in this session. The destination and travel details are not verified.',
    summaryDestination: 'Destination entered', summaryDuration: 'Requested length', clearDraft: 'Clear draft',
    requestRequired: 'Please describe your trip in at least 5 characters.', requestTooLong: 'The trip description is too long. The limit is 1,200 characters.', destinationTooLong: 'Destination names must be 120 characters or fewer.', durationInvalid: 'Trip length must be from 1 to 3 days.',
    daysInvalid: 'Trip length must be between 1 and 3 days.', durationDetected: 'Trip length was recognized from your request.',
    fixtureLabel: 'Illustrative only · not a verified destination or live recommendation',
  },
  ar: {
    destinationLabel: 'الوجهة التي تفكر فيها', destinationPlaceholder: 'اسم المدينة أو المنطقة',
    durationLabel: 'مدة الرحلة', durationOptional: 'لم تحدد بعد', durationDays: '{value} أيام',
    sessionNotice: 'تبقى هذه المسودة في هذه الصفحة فقط؛ لا تُرسل ولا تُحفظ.',
    clarificationTitle: 'نحتاج إلى توضيح بعض التفاصيل لإعداد المسودة:', askDestination: 'أي مدينة أو منطقة تفكر فيها؟', askDuration: 'كم تستغرق الرحلة؟ (من يوم إلى ٣ أيام)',
    capturedTitle: 'تم تسجيل متطلبات الرحلة', capturedLocal: 'هذه مسودة مؤقتة ضمن الجلسة. الوجهة وتفاصيل السفر غير مؤكدة.',
    summaryDestination: 'الوجهة التي أدخلتها', summaryDuration: 'المدة المطلوبة', clearDraft: 'مسح المسودة',
    requestRequired: 'يرجى وصف الرحلة بخمسة أحرف على الأقل.', requestTooLong: 'وصف الرحلة طويل جدًا؛ الحد الأقصى ١٢٠٠ حرف.', destinationTooLong: 'يجب ألا يتجاوز اسم الوجهة ١٢٠ حرفًا.', durationInvalid: 'يجب أن تكون مدة الرحلة من يوم إلى ٣ أيام.',
    daysInvalid: 'يجب أن تكون مدة الرحلة من يوم إلى ٣ أيام.', durationDetected: 'تم التعرف على مدة الرحلة من وصفك.',
    fixtureLabel: 'للتوضيح فقط · ليست وجهة موثقة أو توصية مباشرة',
  },
} satisfies Record<Locale, Record<string, string>>;

export type TripMessageKey = keyof typeof tripMessages['fa-IR'];
