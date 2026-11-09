# بستهٔ کارهای مستقل مالک برای AI Tourism — Phase 4

**نسخه:** ۱.۰  
**تاریخ:** ۲۰۲۶-۱۱-۰۹  
**وضعیت:** آمادهٔ بازبینی مالک و استفاده به‌عنوان ورودی task مهندسی؛ نه انتشار به مخزن و نه مجوز production

## خلاصهٔ پنج خروجی

| # | خروجی | فایل اصلی | نتیجه |
|---|---|---|---|
| ۱ | قرارداد RAG | `01_rag_contract/OWNER_RAG_RETRIEVAL_PORT_CONTRACT_v1.0.md` | مرز typed، evidence/provenance، locale، timeout/error و جدایی responsibility |
| ۲ | ارزیابی RAG | `02_rag_evaluation/RAG_EVALUATION_SET_v1.0.json` و protocol | ۲۶ سناریو × ۳ زبان = ۷۸ سؤال؛ ۱۴ مثبت و ۱۲ abstention |
| ۳ | پژوهش و بستهٔ محتوا | `03_content_research/` | صف جغرافیای تکمیلی فارس (۱۵ ردیف جدید + ارجاع باغ ارم)، ۸ موضوع خوراکی جدید، منابع مستقل Visit Iran و دو منبع UNESCO برای منظر ساسانی؛ بدون انتشار |
| ۴ | ماتریس پوشش | `04_coverage/CONTENT_COVERAGE_MATRIX_v1.0.csv` و گزارش | شمارش دقیق ۱۱ spatial proposal، ۵ food proposal، ۲۹ claim، ۲۳ منبع، مختصات و unknownها |
| ۵ | معماری UX/محصول | `05_ux_architecture/RECOMMENDATION_EVIDENCE_UX_ARCHITECTURE_v1.0.md` | flow نتیجهٔ evidence-first، حالت‌های empty/abstain، تفکیک غذا از مکان، UX نقشه/itinerary |

## کشف مهم دربارهٔ مخزن

در زمان کار، HEAD شاخهٔ `fix/initialize-database-powershell-inspect-v1` در GitHub برابر `5b8f2384d08f747b13b1f319b2e2480e73f5d353` بود و commit پیام `add : modified by Codex Phase#4` داشت؛ والد آن `a921277...` است. برخی اسناد Phase 4 داخل repo هنوز HEAD قبلی `a921277...` را نوشته‌اند. من هیچ تغییری در GitHub، branch، main یا فایل‌های محلی انجام نداده‌ام.

بستهٔ موجود `engineering/data-research/shiraz_fars_candidate_content_v2` قبلاً ۱۱ پیشنهاد مکانی برای غنی‌سازی هویت‌های موجود و ۵ پیشنهاد خوراکی غیرمکانی داشته است؛ بنابراین آن‌ها دوباره تولید نشده‌اند. وضعیت همهٔ آن‌ها هنوز `needs_review`, `pending`, `publishable=false` است. گزارش Codex می‌گوید در آخرین اجرای ثبت‌شده، production catalogue خالی بود و RAG معنایی اجرا نشده است.

## نکتهٔ مهم دربارهٔ عدد پوشش

پر بودن نام/توصیف در سه زبان به معنی ترجمهٔ بازبینی‌شده نیست. ۱۱/۱۱ مکان و ۵/۵ غذا فیلدهای سه‌زبانهٔ پیش‌نویس دارند، اما هیچ‌کدام native-editorial sign-off ندارند. ۹ مختصات spatial از Wikipedia به‌عنوان `representative_point` ثانویه هستند و ۲ مختصات UNESCO، `property_reference` هستند. تعداد ورودی بازدیدکنندهٔ مستقل و تأییدشده: صفر.

## مواردی که عمداً انجام نشد

- هیچ فایلی در repository یا GitHub نوشته/ویرایش نشد.
- هیچ branch, commit, push, PR, merge یا deployment انجام نشد.
- هیچ DB یا migration اجرا/تغییر داده نشد؛ shared database دست‌نخورده است.
- هیچ data proposal به production publish نشد.
- owner RAG اجرا یا benchmark نشد؛ هیچ embedding model/dimension/reranker انتخاب نشد.
- هیچ external paid AI, SMS یا map/weather provider فراخوانی نشد.
- هیچ access/difficulty/safety/price/hour/availability/route fact حدس زده نشد.

## نحوهٔ استفاده در task Codex بعدی

این بسته را به‌عنوان ورودی task بررسی کن، نه دستور اجرای همه‌چیز یکباره. یک task قابل‌قبول باید ابتدا interface/adapter و deterministic fake contract tests را بسازد؛ سپس، فقط با owner RAG callable/API که مالک فراهم می‌کند، adapter واقعی را متصل کند؛ evaluation harness را read-only اجرا کند؛ و candidate content import را در proposal/review layer نگه دارد. هیچ publish path، migration یا shared DB mutation بدون approval صریح مجاز نیست.

### بلوکر واحد برای اتصال واقعی RAG

این بسته schema و behavior را مشخص می‌کند، اما نام Python callable، signature واقعی، نوع deployment و wire format سیستم RAG مستقل مالک را نمی‌تواند از GitHub پروژهٔ گردشگری حدس بزند. پیش از adapter واقعی، آن interface باید از پروژهٔ RAG مالک به‌صورت مستند/کد مرجع ارائه شود. این بلوکر مانع پیاده‌سازی قرارداد و harness fake نیست.
