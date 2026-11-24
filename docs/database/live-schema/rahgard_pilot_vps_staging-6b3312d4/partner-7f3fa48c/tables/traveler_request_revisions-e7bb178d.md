# partner.traveler_request_revisions

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** نسخه‌های تغییرناپذیر/بازنگری‌شده درخواست و برنامه اشتراک‌گذاری‌شده با سازمان.
- **دسترسی خواندن:** Only active recipient members and traveler while share remains active.
- **دسترسی نوشتن:** Created by the revision-capture function; no direct client write grant.
- **نمایش عمومی:** Private; snapshots can contain sensitive trip requirements.
- **API مدل/مسیر:** Read through protected organization request/revision routes.
- **فیلد فرم UI:** PartnerWorkspace protected inbox and request/itinerary views.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'revision_id' | 'uuid' | خیر | 'gen_random_uuid()' | شناسه نسخه بازنگری. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'share_id' | 'uuid' | خیر | — | اشتراک مرتبط. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'organization_id' | 'uuid' | خیر | — | سازمان دریافت‌کننده. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'revision_number' | 'integer' | خیر | — | شماره ترتیبی نسخه برای همان اشتراک. | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'trip_version' | 'integer' | خیر | — | نسخه برنامه/سفر مرجع. | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'event_kind' | 'text' | خیر | — | نوع رویداد نسخه مانند اشتراک جدید یا بازنگری. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'request_snapshot' | 'jsonb' | خیر | — | نمای ثابت و محدودشده شرایط سفر در لحظه ارسال؛ اطلاعات شخصی باید کنترل دسترسی داشته باشد. | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |
| 'itinerary_snapshot' | 'jsonb' | خیر | '[redacted string default]' | نمای ثابت برنامه سفر در لحظه ارسال. | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |
| 'created_by' | 'uuid' | خیر | — | Traveler account whose authorized change generated this immutable revision. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | زمان ایجاد نسخه. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'is_synthetic' | 'boolean' | خیر | 'false' | علامت داده آزمایشی؛ نباید در صندوق تولیدی به کاربر واقعی نشان داده شود. | true / false |

## محدودیت‌ها و ارتباط‌ها

- **traveler_request_revisions_event_kind_check** (`c`): `CHECK ((event_kind = ANY (ARRAY['request_shared'::text, 'request_revised'::text])))`
- **traveler_request_revisions_itinerary_snapshot_check** (`c`): `CHECK ((jsonb_typeof(itinerary_snapshot) = 'object'::text))`
- **traveler_request_revisions_request_snapshot_check** (`c`): `CHECK ((jsonb_typeof(request_snapshot) = 'object'::text))`
- **traveler_request_revisions_revision_number_check** (`c`): `CHECK ((revision_number > 0))`
- **traveler_request_revisions_trip_version_check** (`c`): `CHECK ((trip_version > 0))`
- **traveler_request_revisions_created_by_fkey** (`f`): `FOREIGN KEY (created_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **traveler_request_revisions_share_id_organization_id_fkey** (`f`): `FOREIGN KEY (share_id, organization_id) REFERENCES partner.traveler_request_shares(share_id, organization_id) ON DELETE CASCADE`
- **traveler_request_revisions_pkey** (`p`): `PRIMARY KEY (revision_id)`
- **traveler_request_revisions_revision_id_organization_id_key** (`u`): `UNIQUE (revision_id, organization_id)`
- **traveler_request_revisions_share_id_revision_number_key** (`u`): `UNIQUE (share_id, revision_number)`

## ایندکس‌ها

- `ix_traveler_request_revisions_org`: `CREATE INDEX ix_traveler_request_revisions_org ON partner.traveler_request_revisions USING btree (organization_id, created_at DESC)`
- `traveler_request_revisions_pkey`: `CREATE UNIQUE INDEX traveler_request_revisions_pkey ON partner.traveler_request_revisions USING btree (revision_id)`
- `traveler_request_revisions_revision_id_organization_id_key`: `CREATE UNIQUE INDEX traveler_request_revisions_revision_id_organization_id_key ON partner.traveler_request_revisions USING btree (revision_id, organization_id)`
- `traveler_request_revisions_share_id_revision_number_key`: `CREATE UNIQUE INDEX traveler_request_revisions_share_id_revision_number_key ON partner.traveler_request_revisions USING btree (share_id, revision_number)`

## سیاست‌های RLS

- `traveler_revision_insert`: command=a, roles=[], using=`—`, with_check=`((created_by = partner.current_actor_id()) AND (EXISTS ( SELECT 1    FROM partner.traveler_request_shares s   WHERE ((s.share_id = traveler_request_revisions.share_id) AND (s.traveler_id = partner.current_actor_id()) AND (s.revoked_at IS NULL)))))`
- `traveler_revision_read`: command=r, roles=[], using=`(EXISTS ( SELECT 1    FROM partner.traveler_request_shares s   WHERE ((s.share_id = traveler_request_revisions.share_id) AND (s.revoked_at IS NULL) AND ((s.traveler_id = partner.current_actor_id()) OR partner.has_active_membership(s.organization_id, partner.current_actor_id())))))`, with_check=`—`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **11**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
