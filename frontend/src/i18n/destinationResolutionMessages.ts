import type { Locale } from './messages';

export const destinationResolutionMessages = {
  'fa-IR': {
    unavailable: 'فعلاً امکان بررسی مقصد در فهرست تأییدشده را نداریم. نامی که نوشته‌ای همان‌طور حفظ شده؛ می‌توانی آن را ویرایش یا روشن‌تر کنی.',
    empty: 'در حال حاضر مقصد تأییدشده‌ای برای تطبیق در دسترس نیست. نام واردشده تأیید نشده است؛ می‌توانی آن را ویرایش کنی یا بعداً دوباره تلاش کنی.',
    notFound: 'نام «{phrase}» با نام یا نام مستعار تأییدشده‌ای تطبیق نداشت. لطفاً نام را ویرایش یا دقیق‌تر کن.',
    ambiguous: 'برای «{phrase}» چند مقصد تأییدشده پیدا شد. کدام‌یک را در نظر داری؟',
    selected: 'این مقصد برای همین پیش‌نویس انتخاب شد؛ هنوز برنامه یا داده‌ای ذخیره نشده است.',
    loading: 'در حال بررسی نام در فهرست مقصدهای تأییدشده…',
    none: 'اگر هیچ‌کدام مدنظرت نیست، نام مقصد را در متن اصلی اصلاح یا دقیق‌تر کن.',
  },
  'en-US': {
    unavailable: 'We cannot check this name against the approved destination list right now. Your wording is preserved; you can edit it or add detail.',
    empty: 'There are currently no approved destinations available to match. The entered name is unverified; you can edit it or try again later.',
    notFound: '“{phrase}” did not exactly match an approved name or alias. Please edit the name or make it more specific.',
    ambiguous: 'More than one approved destination matches “{phrase}”. Which one did you mean?',
    selected: 'This destination is selected for this draft only; no plan or data has been saved.',
    loading: 'Checking the name against the approved destination list…',
    none: 'If none is the intended place, edit the original request with a clearer name.',
  },
  ar: {
    unavailable: 'لا يمكننا مطابقة هذا الاسم مع قائمة الوجهات المعتمدة الآن. احتفظنا بعبارتك كما كتبتها؛ يمكنك تعديلها أو إضافة توضيح.',
    empty: 'لا توجد حاليًا وجهات معتمدة متاحة للمطابقة. الاسم الذي أدخلته غير موثق؛ يمكنك تعديله أو المحاولة لاحقًا.',
    notFound: 'لم يطابق «{phrase}» اسمًا أو اسمًا بديلًا معتمدًا. يرجى تعديل الاسم أو تحديده بدقة أكبر.',
    ambiguous: 'تطابق «{phrase}» مع أكثر من وجهة معتمدة. أيّها تقصد؟',
    selected: 'تم اختيار هذه الوجهة لهذه المسودة فقط؛ لم يتم حفظ خطة أو بيانات.',
    loading: 'جارٍ التحقق من الاسم في قائمة الوجهات المعتمدة…',
    none: 'إذا لم تكن أي منها مقصودة، فعدّل نص الطلب الأصلي باسم أوضح.',
  },
} satisfies Record<Locale, Record<string, string>>;
