import type { Locale } from '../i18n/messages';

export const authMessages: Record<Locale, {
  signIn: string; signOut: string; phone: string; phoneHelp: string; sendCode: string;
  code: string; verify: string; back: string; loading: string; codeSent: string;
  genericError: string; invalidCode: string; rateLimited: string; close: string;
}> = {
  'fa-IR': {
    signIn: 'ورود', signOut: 'خروج', phone: 'شماره همراه', phoneHelp: 'شماره همراه ایران را وارد کن؛ مانند ۰۹۱۲۱۲۳۴۵۶۷.',
    sendCode: 'دریافت کد', code: 'کد پیامک‌شده', verify: 'تأیید و ورود', back: 'تغییر شماره',
    loading: 'در حال بررسی…', codeSent: 'اگر ورود امکان‌پذیر باشد، کد ارسال می‌شود.',
    genericError: 'فعلاً امکان ورود نیست. کمی بعد دوباره تلاش کن.', invalidCode: 'کد معتبر نیست یا زمان آن گذشته است.',
    rateLimited: 'درخواست‌های زیادی ثبت شده؛ کمی بعد دوباره تلاش کن.', close: 'بستن',
  },
  'en-US': {
    signIn: 'Sign in', signOut: 'Sign out', phone: 'Mobile number', phoneHelp: 'Enter an Iranian mobile number, for example 09121234567.',
    sendCode: 'Send code', code: 'SMS code', verify: 'Verify and sign in', back: 'Change number',
    loading: 'Checking…', codeSent: 'If sign-in can proceed, a code will be sent.',
    genericError: 'Sign-in is unavailable right now. Please try again later.', invalidCode: 'That code is invalid or has expired.',
    rateLimited: 'Too many requests. Please try again later.', close: 'Close',
  },
  ar: {
    signIn: 'تسجيل الدخول', signOut: 'تسجيل الخروج', phone: 'رقم الهاتف المحمول', phoneHelp: 'أدخل رقمًا إيرانيًا، مثل 09121234567.',
    sendCode: 'إرسال الرمز', code: 'رمز الرسالة', verify: 'تحقق وسجّل الدخول', back: 'تغيير الرقم',
    loading: 'جارٍ التحقق…', codeSent: 'إذا أمكن تسجيل الدخول، فسيتم إرسال رمز.',
    genericError: 'تسجيل الدخول غير متاح الآن. حاول لاحقًا.', invalidCode: 'الرمز غير صحيح أو انتهت صلاحيته.',
    rateLimited: 'طلبات كثيرة. حاول مرة أخرى لاحقًا.', close: 'إغلاق',
  },
};
