import type { Locale } from '../i18n/messages';

export const authMessages: Record<Locale, {
  signIn: string; signOut: string; phone: string; phoneHelp: string; sendCode: string;
  code: string; verify: string; back: string; loading: string; codeSent: string;
  genericError: string; invalidCode: string; requestUnavailable: string; close: string;
  deleteAccount: string; confirmDeleteAccount: string; travelerSignIn: string; smsUnavailable: string;
}> = {
  'fa-IR': {
    signIn: 'ورود', signOut: 'خروج', phone: 'شماره همراه', phoneHelp: 'شماره همراه ایران را وارد کنید؛ مانند ۰۹۱۲۱۲۳۴۵۶۷.',
    sendCode: 'دریافت کد', code: 'کد پیامک‌شده', verify: 'تأیید و ورود', back: 'تغییر شماره', loading: 'در حال بررسی…',
    codeSent: 'اگر ورود امکان‌پذیر باشد، کد ارسال می‌شود.', genericError: 'فعلاً ورود در دسترس نیست. کمی بعد دوباره تلاش کنید.',
    invalidCode: 'کد نادرست است یا اعتبار آن پایان یافته است.',
    requestUnavailable: 'فعلاً نمی‌توان ورود را ادامه داد. کمی بعد دوباره تلاش کنید.', close: 'بستن',
    deleteAccount: 'حذف حساب', confirmDeleteAccount: 'حساب و همه محتوای شخصی مرتبط حذف شود؟ این کار برگشت‌پذیر نیست.',
    travelerSignIn: 'ورود مسافر',
    smsUnavailable: 'ارسال پیامک فعلاً فعال نیست؛ هیچ کدی ارسال نشده است. ورود با شماره همراه پس از پیکربندی سرویس پیامک در دسترس خواهد بود.',
  },
  'en-US': {
    signIn: 'Sign in', signOut: 'Sign out', phone: 'Mobile number', phoneHelp: 'Enter an Iranian mobile number, for example 09121234567.',
    sendCode: 'Send code', code: 'SMS code', verify: 'Verify and sign in', back: 'Change number', loading: 'Checking…',
    codeSent: 'If sign-in can proceed, a code will be sent.', genericError: 'Sign-in is unavailable right now. Please try again later.',
    invalidCode: 'That code is invalid or has expired.',
    requestUnavailable: 'We cannot continue sign-in right now. Please try again later.', close: 'Close',
    deleteAccount: 'Delete account', confirmDeleteAccount: 'Delete your account and all associated personal content? This cannot be undone.',
    travelerSignIn: 'Traveler sign in',
    smsUnavailable: 'SMS delivery is unavailable until a real SMS provider is configured. No code has been sent.',
  },
  ar: {
    signIn: 'تسجيل الدخول', signOut: 'تسجيل الخروج', phone: 'رقم الهاتف المحمول', phoneHelp: 'أدخل رقم هاتف إيراني، مثل 09121234567.',
    sendCode: 'إرسال الرمز', code: 'رمز الرسالة', verify: 'تحقق وسجّل الدخول', back: 'تغيير الرقم', loading: 'جارٍ التحقق…',
    codeSent: 'إذا أمكن تسجيل الدخول، فسيتم إرسال رمز.', genericError: 'تسجيل الدخول غير متاح الآن. حاول لاحقًا.',
    invalidCode: 'الرمز غير صحيح أو انتهت صلاحيته.',
    requestUnavailable: 'لا يمكننا متابعة تسجيل الدخول الآن. حاول مرة أخرى لاحقًا.', close: 'إغلاق',
    deleteAccount: 'حذف الحساب', confirmDeleteAccount: 'هل تريد حذف حسابك وكل المحتوى الشخصي المرتبط به؟ لا يمكن التراجع عن هذا الإجراء.',
    travelerSignIn: 'تسجيل دخول المسافر',
    smsUnavailable: 'إرسال الرسائل القصيرة غير متاح حاليًا؛ لم يتم إرسال أي رمز. سيتاح الدخول بالهاتف بعد إعداد مزود رسائل حقيقي.',
  },
};
