# پروتکل ارزیابی RAG گردشگری — نسخه ۱.۰

**وضعیت:** مجموعهٔ اولیهٔ gold؛ بازبینی مالک و ویراستار سه‌زبانه لازم است.  
**تعداد:** ۲۶ سناریو × ۳ زبان = ۷۸ پرسش (۱۴ سناریوی مثبت و ۱۲ سناریوی abstention).

## 1. هدف

سنجش کیفیت اتصال owner-RAG بدون انتخاب الگوریتم، مدل embedding، reranker یا provider. این ارزیابی باید نشان دهد سیستم در بازیابی شواهد واقعی، زبان‌های مختلف، حفظ provenance، پرهیز از استنتاج عملیاتی و abstention چه رفتاری دارد.

## 2. ساختار مجموعه

- ۱۴ سناریوی مثبت برای واقعیت‌های تاریخی/جغرافیایی/فرهنگی و خوراکی‌های منبع‌دار.
- ۱۲ سناریوی منفی/غیرقابل‌پاسخ برای ساعات و قیمت امروز، دسترسی، سختی مسیر، ورودی، زمان مسیر، رستوران فعال، آلرژن، آب‌وهوا، حمل‌ونقل، دستور کامل/کالری و رزرو.
- هر سناریو یک سؤال فارسی، انگلیسی و عربی دارد؛ ۷۸ پرسش کل.
- `expected_source_ids` شناسه‌های source register هستند؛ هنگام آماده‌سازی corpus باید به document/chunk/claim ID واقعی mapping شوند.

## 3. روش اجرا

1. Gold set را نسخه‌گذاری کنید و پس از شروع نمره‌دهی، سؤال یا expected evidence را بی‌ردپا تغییر ندهید.
2. corpus آزمایشی را فقط از proposalهایی بسازید که مالک/ویراستار مستقل تأیید و به مسیر انتشار آزمایشی مصوب منتقل کرده است. تا پیش از تأیید، این داده‌ها برای تست رابط fake می‌توانند fixture باشند، ولی نباید خروجی production retrieval محسوب شوند.
3. query را در locale اصلی اجرا کنید؛ پاسخ در locale خواسته‌شده باشد. برای هر اجرای فارسی/انگلیسی/عربی، top-k و شناسه evidenceها را ذخیره کنید.
4. پاسخ تولیدشده را به claimهای اتمی تقسیم و برای هر claim، source id و claim/document/chunk id ثبت کنید.
5. پاسخ منفی باید صریحاً کمبود مدرک را اعلام کند. بازیابی متن نامرتبط نباید به پاسخ مثبت تبدیل شود.
6. دو reviewer انسانی مستقل، relevance و faithfulness را بررسی کنند؛ اختلاف با adjudication ثبت شود.
7. نتایج به تفکیک locale، corpus، نوع پرسش و نوع خطا گزارش شوند. امتیاز تجمیعی به تنهایی قابل قبول نیست.

## 4. معیارها و target پیشنهادی برای مذاکره

| معیار | تعریف | Target پیشنهادی اولیه |
|---|---|---:|
| Recall@5 | سهم expected evidence IDهای بازیابی‌شده در top 5 | ≥ 0.85 در هر زبان |
| MRR@10 | معکوس رتبهٔ اولین evidence معتبر | ≥ 0.80 در هر زبان |
| nDCG@10 | کیفیت ترتیب relevance با درجات relevance انسانی | ≥ 0.80 در هر زبان |
| Evidence precision@5 | سهم موارد top 5 که برای پرسش مرتبط و مجازند | ≥ 0.90 |
| Claim-level faithfulness | ادعاهای پاسخ که مستقیم از evidence پشتیبانی می‌شوند | ≥ 0.95 |
| Citation completeness | ادعاهای factual دارای provenance معتبر | 100% |
| Abstention precision | سؤال‌های فاقد evidence که به‌درستی abstain می‌کنند | ≥ 0.98 |
| Unsafe unsupported claim | ادعای بدون مدرک دربارهٔ دسترسی/ایمنی/آلرژن/قیمت/زمان جاری | 0 |
| Locale correctness | پاسخ در زبان خواسته‌شده، بدون قاطی‌شدن بی‌دلیل زبان‌ها | ≥ 0.98 |

این اعداد **پیشنهاد برای تأیید مالک** هستند، نه معیار مصوب یا نتیجهٔ اندازه‌گیری‌شده. قبل از تبدیل به gate باید با حجم corpus، نوع سؤال و خطر هر دسته مذاکره شوند. برای safety/accessibility/allergen/booking، حتی یک خطای مثبتِ بی‌مدرک باید شکست بحرانی باشد.

## 5. دسته‌بندی خطاها

- `missed_relevant_evidence`: سند صحیح در top-k نیست.
- `wrong_entity`: بازیابی مکان/غذای مشابه ولی هویت اشتباه.
- `wrong_locale`: شواهد یا پاسخ به زبان نامناسب.
- `source_conflict_hidden`: اختلاف منابع نادیده گرفته شده.
- `stale_evidence`: اطلاعات منقضی یا بی‌اعتبار استفاده شده.
- `unsupported_claim`: واقعیت خارج از شواهد تولید شده.
- `unsafe_inference`: دسترسی/سختی/ایمنی/آلرژن/قیمت/وضعیت جاری حدس زده شده.
- `abstention_failure`: مدل در نبود evidence پاسخ قطعی داده است.
- `over_abstention`: evidence معتبر موجود بوده ولی پاسخ به‌اشتباه خالی شده است.
- `spatial_culinary_leak`: غذا به‌عنوان مکان یا stop/موقعیت نمایش داده شده است.

## 6. گزارش الزامی هر اجرا

- git commit / corpus version / retrieval version / contract version؛
- locale، scenario IDs، top-k evidence IDs، source IDs و rank؛
- Recall@k/MRR/nDCG/precision به تفکیک locale؛
- claim-level citation coverage و faithfulness انسانی؛
- abstention precision/recall؛
- critical unsupported claims count؛
- latency percentile، timeout/error، retry count؛
- prompt text و user PII در telemetry ذخیره نشوند؛ برای اشکال‌زدایی از query ID و مورد مصنوعی‌شده استفاده شود.

## 7. موارد خارج از این پروتکل

این مجموعه embedding benchmark، مقایسهٔ مدل‌ها یا آزمون performance مقیاس بزرگ نیست. هیچ مدل یا provider را انتخاب نمی‌کند. اجرای آن روی RAG مالک باید فقط پس از قرارداد API و مجوز صریح داده انجام شود.
