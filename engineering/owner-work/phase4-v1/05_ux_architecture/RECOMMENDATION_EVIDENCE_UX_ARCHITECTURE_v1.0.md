# معماری تجربهٔ پیشنهاد سفر، شواهد و محتوای خوراکی — نسخه ۱.۰

**وضعیت:** سند پیشنهادی همسو با تصمیم‌های پذیرفته‌شدهٔ پروژه؛ نیازمند تأیید owner برای جزئیات خارج از ADRها  
**تاریخ:** ۲۰۲۶-۱۱-۰۹

## 1. وعدهٔ محصول

سامانه باید برای مسافر فارسی‌زبان تجربه‌ای شبیه مشاور سفر قابل اعتماد ارائه کند: درخواست طبیعی را می‌فهمد، فقط سؤال ضروری می‌پرسد، مقصدهای قابل دفاع و مستند را پیشنهاد می‌دهد، محدودیت‌های سفر را جدی می‌گیرد و هنگام نبود داده صادقانه مکث می‌کند. کیفیت بصری مهم است اما نباید کمبود داده را با تصویر یا متن ساختگی بپوشاند.

## 2. Pipeline پیشنهادی

```text
1. Natural-language intake (fa/en/ar)
2. Deterministic parse + user-confirmable normalized request
3. Requirement assessment (hard / soft / advisory consent)
4. RetrievalPort calls (one corpus per call; evidence + source metadata)
5. Evidence validation (publication, version, freshness, locale, identity)
6. Deterministic eligibility and ranking (application-owned)
7. Evidence-backed explanation and explicit unknowns
8. Separate food discovery block (non-spatial)
9. 1–3 day approximate itinerary draft (only from eligible spatial stops)
10. Edit / save / export under authenticated ownership
```

RAG می‌تواند نامزدهای معنایی و evidence بیاورد؛ LLM می‌تواند متن درخواست را parse یا توضیح را phrasing کند. هیچ‌یک hard constraints، consent، safety/accessibility، publication یا eligibility را تعیین نمی‌کند.

## 3. مدل نتیجهٔ پیشنهادی

هر نتیجه مکانی باید حداقل این بخش‌ها را داشته باشد:

- canonical identity + localized name;
- why relevant: فقط دلیل‌هایی که به requirement و claim مشخص وصل‌اند؛
- evidence/source list با نام منبع و لینک؛
- freshness / reviewed status یا warning;
- coordinate role؛ فقط اگر لازم است، کاربر بفهمد نقطهٔ نقشه نمایندهٔ محدوده است یا property point یا ورودی واقعی؛
- unknown fields: access, difficulty, hours, ticket, duration, transit, parking, safety;
- match explanation متنی/قابل فهم، نه درصد کیفیت یا امتیاز ساختگی.

نتیجهٔ خوراکی مدل جدا دارد:

- نام/دسته/توصیف فرهنگی با ادعاهای source-backed؛
- تفاوت نسخه‌های recipe با attribution روشن؛
- هیچ map pin، distance، route stop، venue availability، price یا dietary/allergen badge بدون source مستقل.

## 4. رفتارهای state محور UI

| وضعیت backend/domain | تجربهٔ کاربر | ممنوع |
|---|---|---|
| `available` با evidence معتبر | کارت محتوایی مستند + دلیل + منبع + unknownها | درصد relevance یا star ساختگی |
| `empty` / `no_evidence` | توضیح روشن «در دادهٔ تأییدشده مورد کافی نداریم» و امکان اصلاح درخواست | پرکردن فهرست از inspiration fixtures |
| `unavailable` | حالت موقت عدم دسترسی به داده و دکمه تلاش مجدد محدود | نشان دادن cache قدیمی به‌عنوان دادهٔ امروز |
| `needs_confirmation` | سؤال فقط دربارهٔ فیلد لازم/متناقض؛ حفظ متن اصلی | رد کردن قید سخت به کمک مدل |
| `partial` | پاسخ به قسمت دارای منبع، بخش نامعلوم جدا و برجسته | تبدیل پاسخ جزئی به قطعیت کامل |
| source stale/revoked | حذف از پاسخ زنده یا اخطار، طبق policy | استفادهٔ بی‌صدا از دادهٔ منقضی |

## 5. طراحی دیداری

از direction موجود `Contemporary Iranian Travel Editorial` استفاده شود: تایپوگرافی فارسی خوانا، فضای منفی، ترکیب‌بندی editorial، عکس واقعیِ دارای حقوق، و رنگ‌های طبیعی. نیازی به طراحی سیستم دوم یا داشبورد admin در این تسک نیست.

- صفحهٔ سفر، یک روایت پیوسته باشد: مقصد اصلی، گزینه‌های جایگزین، شواهد، سپس طرح روزانه.
- recommendation cards نباید همه یک قالب سنگین/گرد داشته باشند؛ یک گزینهٔ lead و گزینه‌های مقایسه‌ای به‌صورت editorial.
- منبع و هشدارها بخشی از کارت هستند، نه ریزنوشته‌ای پنهان.
- empty state باید به‌جای تصویر جعلی مقصد، تصویر خنثی/illustrative با برچسب مشخص داشته باشد.
- عکس مستند هر مقصد باید از asset pipeline مجاز و metadata attribution بیاید؛ AI art یا image search result مدرک یک واقعیت مکانی نیست.

## 6. نقشه، مسیر و itinerary

- map pin فقط با مختصات قابل دفاع و role صریح.
- `representative_point` صرفاً برای دید کلی؛ نه مسیریابی تا ورودی.
- `property_reference` مرکز/نقطهٔ مرجع property است؛ نه gate یا parking.
- route/directions تنها وقتی ممکن است که entrance/access point و provider معتبر و تازه وجود داشته باشد.
- غذا concept است و روی map یا itinerary نمی‌آید.
- برنامهٔ ۱ تا ۳ روزه تقریبی و قابل ویرایش است؛ durationهای نامعلوم صریحاً نامعلوم‌اند. ترتیب stopها به معنی optimize شدن route نیست.
- booking/payment transaction خارج از MVP؛ فقط outbound link allowlist در صورت تأیید.

## 7. حریم خصوصی و استفاده از AI

- متن اولیهٔ سفر و شناسهٔ account بدون ضرورت به RAG/Provider Gateway داده نشود.
- Retrieval فقط query حداقلی و filters server-generated دریافت کند.
- هیچ provider/model selector برای مسافر نمایش داده نشود.
- external processing تا زمان تأیید data residency, consent, retention, secret handling و admin gates انجام نشود.
- خطاها provider-neutral و localized باشند؛ endpoint و model name در response عمومی نیاید.
- محتوای بازیابی‌شده untrusted است و نباید prompt injection یا instruction را به سطح سیاست منتقل کند.

## 8. معیارهای UX و acceptance

1. هر factual recommendation claim در سه locale دارای citation/provenance قابل بازکردن باشد.
2. accessibility/safety hard constraints fail closed باشند؛ مدل هیچ‌وقت آن‌ها را waiver نکند.
3. no-evidence و service-unavailable دو state متفاوت داشته باشند.
4. غذا در UI جدا از مکان و نقشه نمایش داده شود.
5. unknown ساعت/قیمت/سختی به‌صورت unknown نمایش داده شود و مقدار فرضی ساخته نشود.
6. LTR/RTL، اعداد، URL و نام‌های mixed-script در هر سه locale تست شوند.
7. صفحهٔ موبایل با keyboard، safe-area و PWA state سالم بماند.
8. کاربر بتواند با حفظ متن درخواست، فیلدهای استخراج‌شده را بررسی/اصلاح کند.
9. هیچ UI score بی‌پشتوانه، star، rating یا درصد تطابق مصنوعی وجود نداشته باشد.
10. تصاویر محصول از UI fixture به‌عنوان evidence توصیه استفاده نشوند.

## 9. تصمیم‌های حل‌نشده که نباید پنهانی اجرا شوند

- pilot geography و وعدهٔ دقیقی که باید پوشش داده شود؛
- source rights/editorial owner/freshness cadence و زبان‌های واقعاً آماده؛
- owner RAG callable entrypoint و integration topology؛
- provider/data processing region و مجوز live LLM calls؛
- production SMS and account recovery؛
- admin MFA/bootstrap/recovery؛
- hosting, domain, TLS/proxy, backups, monitoring and incident ownership؛
- mobile physical-device acceptance.

این سند هیچ‌یک از تصمیم‌های بالا را به‌جای مالک نمی‌گیرد.
