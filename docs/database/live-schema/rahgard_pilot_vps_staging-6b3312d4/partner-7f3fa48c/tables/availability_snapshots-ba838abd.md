# partner.availability_snapshots

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** Time-bounded availability observation, not a future guarantee.
- **دسترسی خواندن:** Organization member according to availability RLS.
- **دسترسی نوشتن:** POST observation only; do not overwrite history.
- **نمایش عمومی:** Freshness limited by observed_at/valid_until; unknown remains unknown.
- **API مدل/مسیر:** POST /organizations/{organization_id}/availability; workspace GET.
- **فیلد فرم UI:** PartnerWorkspace optional availability observation form/history.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'snapshot_id' | 'uuid' | خیر | 'gen_random_uuid()' | Unique identifier for one time-bounded availability observation. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'organization_id' | 'uuid' | خیر | — | Owning partner organization; tenant boundary used by foreign keys and RLS. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'offer_id' | 'uuid' | خیر | — | Offer whose availability was observed. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'schedule_id' | 'uuid' | بله | — | Related schedule occurrence source; nullable when the observation is not schedule-specific. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'occurrence_starts_at' | 'timestamp with time zone' | بله | — | Start instant of the observed service occurrence, stored as timestamptz. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'occurrence_ends_at' | 'timestamp with time zone' | بله | — | End instant of that occurrence when known; must not precede its start. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'availability_state' | 'text' | خیر | — | Observed state: available, unavailable, limited, unknown, or conflicting. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'available_count' | 'integer' | بله | — | Non-negative observed count when applicable; NULL is required for unknown state. | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'source_kind' | 'text' | خیر | — | Provenance class: partner_asserted, approved_feed, or platform_observation. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'observed_at' | 'timestamp with time zone' | بله | — | Instant when availability was observed; required for available state. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'valid_from' | 'timestamp with time zone' | بله | — | Start of the interval for which this observation is represented as valid. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'valid_until' | 'timestamp with time zone' | بله | — | End of the validity interval; do not treat stale data as current. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'created_by' | 'uuid' | بله | — | User account that submitted the observation, if recorded. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **availability_snapshots_availability_state_check** (`c`): `CHECK ((availability_state = ANY (ARRAY['available'::text, 'unavailable'::text, 'limited'::text, 'unknown'::text, 'conflicting'::text])))`
- **availability_snapshots_available_count_check** (`c`): `CHECK (((available_count IS NULL) OR (available_count >= 0)))`
- **availability_snapshots_check** (`c`): `CHECK ((((availability_state = 'unknown'::text) AND (available_count IS NULL)) OR (availability_state <> 'unknown'::text)))`
- **availability_snapshots_check1** (`c`): `CHECK (((availability_state <> 'available'::text) OR (observed_at IS NOT NULL)))`
- **availability_snapshots_check2** (`c`): `CHECK (((occurrence_ends_at IS NULL) OR (occurrence_starts_at IS NULL) OR (occurrence_ends_at >= occurrence_starts_at)))`
- **availability_snapshots_check3** (`c`): `CHECK (((valid_until IS NULL) OR (valid_from IS NULL) OR (valid_until >= valid_from)))`
- **availability_snapshots_source_kind_check** (`c`): `CHECK ((source_kind = ANY (ARRAY['partner_asserted'::text, 'approved_feed'::text, 'platform_observation'::text])))`
- **availability_snapshots_created_by_fkey** (`f`): `FOREIGN KEY (created_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **availability_snapshots_organization_id_offer_id_schedule_i_fkey** (`f`): `FOREIGN KEY (organization_id, offer_id, schedule_id) REFERENCES partner.offers(organization_id, offer_id, schedule_id) ON DELETE RESTRICT`
- **availability_snapshots_pkey** (`p`): `PRIMARY KEY (snapshot_id)`

## ایندکس‌ها

- `availability_snapshots_pkey`: `CREATE UNIQUE INDEX availability_snapshots_pkey ON partner.availability_snapshots USING btree (snapshot_id)`
- `ix_partner_availability_offer_occurrence`: `CREATE INDEX ix_partner_availability_offer_occurrence ON partner.availability_snapshots USING btree (organization_id, offer_id, occurrence_starts_at, observed_at DESC)`

## سیاست‌های RLS

- `availability_insert`: command=a, roles=[], using=`—`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'availability_operator'::text]) AND ((created_by IS NULL) OR (created_by = partner.current_actor_id())))`
- `availability_select`: command=r, roles=[], using=`(partner.has_active_membership(organization_id, partner.current_actor_id()) OR partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text))`, with_check=`—`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **14**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
