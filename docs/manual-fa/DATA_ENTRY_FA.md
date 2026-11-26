# راهنمای پرکردن فرم‌ها و نگاشت به جدول‌ها
[فهرست اصلی](README.md) — مبنا cab603a7d40cfa35dd20de2ffb12a336d84f56ff. نمونه‌ها آزمایشی‌اند. قید API لزوماً به معنی حضور فیلد در UI نیست؛ نبود فرم مجوز نوشتن مستقیم نیست.

## شرکت — /partners
| ورودی | مثال/معنا | قرارداد API | جدول/فیلد |
|---|---|---|---|
| نام حقوقی | شرکت نمونه سفر پارس | ۱–۲۴۰ نویسه | partner.organizations.legal_name |
| نام نمایشی | سفر پارس | ۱–۲۴۰ | partner.organizations.display_name |
| نوع سازمان | company / individual_business / nonprofit / public_body / other | انتخاب واقعی | partner.organizations.organization_type |
| کشور | IR | دو حرف بزرگ | partner.organizations.registration_country |
| خدمت | تور باغ‌ها | نوع ۱–۸۰، نام ۱–۲۴۰ | partner.services.service_type / service_localizations.display_name |
| شرح و زبان | شرح خدمت، fa-IR/en-US/ar | شرح اختیاری تا ۴۰۰۰ | partner.service_localizations.description/locale |
| اتصال مقصد | انتخاب مقصد منتشرشده | شناسه مثبت، at/serves/near/route_endpoint | partner.service_destinations |
| شاهد اتصال | علت ارتباط | اختیاری تا ۱۰۰۰ | partner.service_destinations.evidence_note |
| زمان‌بندی | opening_window/departure/appointment/event/other | انتخاب، منطقه زمانی تا ۸۰، زمان شروع/پایان | partner.schedules |
| پیشنهاد | tour؛ انتخاب خدمت و زمان | نوع ۱–۸۰، اعتبار اختیاری، ظرفیت صحیح غیرمنفی | partner.offers |
| وضعیت قیمت | known/unknown/not_applicable/conflicting | صفر را جای نامعلوم نزنید | partner.prices.price_state |
| مبلغ | مبلغ واقعی | غیرمنفی، ۱۴ رقم و ۲ اعشار | partner.prices.amount |
| ارز و واحد | IRR؛ واحد و denomination طبق قرارداد | ارز سه حرف بزرگ؛ دو رشته اختیاری تا ۸۰ | partner.prices.currency/denomination/unit |
| مالیات | بله/خیر/نامعلوم | bool یا null | partner.prices.tax_included |
| دسترسی | available/unavailable/limited/unknown/not_applicable | پیشنهاد، زمان‌بندی، وقوع، مشاهده، شروع و پایان اعتبار | partner.availability_snapshots |
| مدارک | مراجع قابل بررسی | ۱–۲۰ مرجع؛ اطلاعات اضافه محرمانه ندهید | partner.verification_cases.evidence_refs |

ترتیب: سازمان → خدمت → مقصد/زمان → پیشنهاد → قیمت/دسترسی → ارسال مدارک. شناسه‌ها تولید/انتخاب می‌شوند؛ UUID آزاد نزنید. فرم مستقل شعبه وجود ندارد. بازبین: verified/needs_information/rejected، سپس approve/reject و سپس activate/deactivate/suspend؛ دلیل ۱۰–۲۰۰۰. شرکت خود را تأیید نکند. پاسخ به درخواست: accepted_as_requested/counter_offer، قیمت پیشنهادی تومان، تاریخ، یادداشت تا ۱۵۰۰ و پیام تا ۲۰۰۰؛ تصمیم مسافر accepted/declined. جداول مرتبط partner.trip_company_responses و traveler_request_revisions.

## کاتالوگ — /admin/catalogue-review
| گام | فیلدهای واقعی و قاعده | مقصد داده |
|---|---|---|
| آرشیو | فایل مطابق preflight؛ ابتدا صف، نه انتشار | operations.dataset_import_batches/files؛ knowledge.destination_candidates/source_candidates |
| ثبت منبع | نام ۱–۵۰۰، نوع ۱–۸۰، ناشر ۱–۲۴۰، عنوان ۱–۵۰۰، HTTPS URL ۱۲–۲۰۴۸، توضیح ۱–۱۰۰۰، مجوز اختیاری تا ۵۰۰ | knowledge.knowledge_sources/source_registry_registration_events |
| بررسی منبع | ناشر، عنوان، گزیده شاهد ۱–۶۰۰ و زمان مشاهده | knowledge.source_verification_reviews |
| بررسی هویت | same_entity (همان مکان)، part_of_or_within (جزء/درون)، nearby_distinct (نزدیک ولی جدا)، unresolved (نامشخص) | knowledge.destination_candidate_reviews |
| تصمیم | accept/approve_new_identity/reject/defer/request_evidence، دلیل ۱–۲۰۰۰، مرجع شاهد و مقصد هدف در صورت نیاز | همان |
| شاهد فیلد | منبع، identity/province/city/coordinates/description، مقدار ۱–۸۰۰۰، گزیده ۱–۶۰۰، تاریخ دریافت | knowledge.destination_candidate_evidence |
| انتشار | کلید ۳–۲۴۰ با حروف کوچک انگلیسی/عدد/_/- و نقش property_reference یا representative_point | knowledge.destinations و catalogue_publication_events |

یک باغ نمونه را فقط بعد از شواهد معتبر هویت، موقعیت، استان/شهر و شرح منتشر کنید. نقطه نماینده ورودی دقیق نیست. ثبت منبع با تأیید منبع فرق دارد؛ انتشار به کنترل سمت سرور وابسته است.

## AI Provider — /admin با ai_provider_admin و MFA
| فیلد | قرارداد / نمونه |
|---|---|
| نام | ۱–۱۰۰؛ مدل آزمایشی Chat |
| provider_kind | lm_studio/openai_compatible |
| Base URL | ۸–۳۰۰؛ فقط endpoint تأییدشده در allowlist |
| auth_mode | none/bearer |
| API key | در HTTPS خصوصی؛ حداکثر ۲۰۴۸، نه Git/DB خام |
| قابلیت و model_id | chat/vision/embedding/reranking فقط پشتیبانی‌شده؛ مدل ۱–۱۶۰ |
| max_tokens | ۱–۴۰۹۶، پیش‌فرض ۸۰۰ |
| timeout_seconds | ۱–۶۰، پیش‌فرض ۲۰ |
| concurrency_limit | ۱–۱۰، پیش‌فرض ۱ |
| تست | discovery/inference؛ سقف خروجی ۱–۶۴ |
| فعال‌سازی | revision معتبر + expected_version |
| fallback | حداکثر ۳ revision؛ پیش‌فرض خاموش |

ترتیب: ذخیره پروفایل → کشف مدل → تست محدود → اعتبارسنجی → فعال‌سازی → درخواست واقعی دستیار با حساب مسافر → مشاهده Usage → Restart/بازخوانی. در خطا rollback به نسخه معتبر. پاسخ مستقیم LM Studio اثبات مسیر Rahgard نیست. جداول ai_provider.profiles/revisions/revision_validations/active_routes/fallback_policy؛ کلید در Vault و تنها secret_ref در DB. ویژگی پشتیبانی‌نشده را فعال نکنید.

## سفر و اطلاعات خودکار
مبدأ، مقصد، تاریخ/مدت، تعداد، بودجه و واحد، علاقه و محدودیت را در فرم تأیید سفر وارد کنید؛ بودجه کل/هر نفر و تومان/ریال را جدا کنید. travel.trips و trip_requirement_revisions، itinerary/stops یا provisional_itineraries و conversation.messages توسط سامانه پر می‌شوند. جدول‌های حساب، OTP، نشست، audit، grant، ledger، Viewها، PostGIS، embedding و امتیاز recommendation فرم SQL عمومی ندارند.

مراجع: [partners.py](../../backend/app/api/partners.py)، [catalogue_review.py](../../backend/app/api/catalogue_review.py)، [provider_admin.py](../../backend/app/api/provider_admin.py)، [traveler.py](../../backend/app/api/traveler.py)، [راهنمای شرکت‌ها](../database/PARTNER_WORKFLOWS.md)، [فرهنگ فیلدها](README.md).
