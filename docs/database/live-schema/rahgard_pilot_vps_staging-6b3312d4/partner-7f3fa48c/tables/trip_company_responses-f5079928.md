# partner.trip_company_responses

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** Company response to an authorized traveler request revision and traveler decision.
- **دسترسی خواندن:** Authorized recipient members and the traveler owning the trip.
- **دسترسی نوشتن:** Company submits response; traveler alone updates decision state.
- **نمایش عمومی:** Private; amounts are proposal fields, not booking/payment transactions.
- **API مدل/مسیر:** POST/GET organization request responses; traveler response and decision routes.
- **فیلد فرم UI:** CompanyResponseActions and traveler response panel.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'response_id' | 'uuid' | خیر | 'gen_random_uuid()' | Unique identifier for the company response. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'client_request_id' | 'uuid' | خیر | — | Client-provided idempotency identifier, unique within a share. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'share_id' | 'uuid' | خیر | — | Traveler-authorized share being answered. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'organization_id' | 'uuid' | خیر | — | Recipient organization and tenant boundary. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'revision_id' | 'uuid' | خیر | — | Exact shared request revision the response addresses. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'trip_id' | 'uuid' | خیر | — | Traveler trip referenced by the share. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'traveler_id' | 'uuid' | خیر | — | Trip owner who receives and decides the response. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'submitted_by' | 'uuid' | خیر | — | Authorized company member who submitted the response. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'response_kind' | 'text' | خیر | — | accepted_as_requested or counter_offer. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'message' | 'text' | خیر | '[redacted string default]' | Company response text, maximum 2000 characters. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'proposed_price_toman' | 'numeric(14,2)' | بله | — | Optional proposed price in Iranian toman; this is not a payment or booking transaction. | عدد ده‌دهی؛ precision و scale از PostgreSQL؛ واحد/ارز باید مستند شود |
| 'proposed_start_date' | 'date' | بله | — | Optional proposed Gregorian ISO date; set together with proposed_end_date. | تاریخ میلادی ISO 8601: YYYY-MM-DD (تبدیل جلالی صرفاً در UI) |
| 'proposed_end_date' | 'date' | بله | — | Optional proposed Gregorian ISO date; must be on or after proposed_start_date. | تاریخ میلادی ISO 8601: YYYY-MM-DD (تبدیل جلالی صرفاً در UI) |
| 'proposed_schedule_notes' | 'text' | خیر | '[redacted string default]' | Optional counter-offer schedule notes, maximum 1500 characters. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'traveler_decision' | 'text' | خیر | '[redacted string default]' | Traveler-only decision: pending, accepted, or declined. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'decided_at' | 'timestamp with time zone' | بله | — | Timestamp of traveler decision; NULL exactly while decision is pending. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'is_synthetic' | 'boolean' | خیر | 'false' | Test marker constrained to false for persisted company responses. | true / false |

## محدودیت‌ها و ارتباط‌ها

- **trip_company_responses_check** (`c`): `CHECK (((proposed_start_date IS NULL) = (proposed_end_date IS NULL)))`
- **trip_company_responses_check1** (`c`): `CHECK (((proposed_end_date IS NULL) OR (proposed_end_date >= proposed_start_date)))`
- **trip_company_responses_check2** (`c`): `CHECK (((response_kind <> 'accepted_as_requested'::text) OR ((proposed_price_toman IS NULL) AND (proposed_start_date IS NULL) AND (proposed_schedule_notes = ''::text))))`
- **trip_company_responses_check3** (`c`): `CHECK (((response_kind <> 'counter_offer'::text) OR ((proposed_price_toman IS NOT NULL) OR (proposed_start_date IS NOT NULL) OR (length(btrim(proposed_schedule_notes)) > 0))))`
- **trip_company_responses_check4** (`c`): `CHECK (((traveler_decision = 'pending'::text) = (decided_at IS NULL)))`
- **trip_company_responses_is_synthetic_check** (`c`): `CHECK ((is_synthetic = false))`
- **trip_company_responses_message_check** (`c`): `CHECK ((length(message) <= 2000))`
- **trip_company_responses_proposed_price_toman_check** (`c`): `CHECK ((proposed_price_toman >= (0)::numeric))`
- **trip_company_responses_proposed_schedule_notes_check** (`c`): `CHECK ((length(proposed_schedule_notes) <= 1500))`
- **trip_company_responses_response_kind_check** (`c`): `CHECK ((response_kind = ANY (ARRAY['accepted_as_requested'::text, 'counter_offer'::text])))`
- **trip_company_responses_traveler_decision_check** (`c`): `CHECK ((traveler_decision = ANY (ARRAY['pending'::text, 'accepted'::text, 'declined'::text])))`
- **trip_company_responses_revision_id_organization_id_fkey** (`f`): `FOREIGN KEY (revision_id, organization_id) REFERENCES partner.traveler_request_revisions(revision_id, organization_id) ON DELETE CASCADE`
- **trip_company_responses_share_id_organization_id_fkey** (`f`): `FOREIGN KEY (share_id, organization_id) REFERENCES partner.traveler_request_shares(share_id, organization_id) ON DELETE CASCADE`
- **trip_company_responses_submitted_by_fkey** (`f`): `FOREIGN KEY (submitted_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **trip_company_responses_traveler_id_fkey** (`f`): `FOREIGN KEY (traveler_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- **trip_company_responses_trip_id_fkey** (`f`): `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- **trip_company_responses_pkey** (`p`): `PRIMARY KEY (response_id)`
- **trip_company_responses_share_id_client_request_id_key** (`u`): `UNIQUE (share_id, client_request_id)`

## ایندکس‌ها

- `ix_trip_company_responses_company`: `CREATE INDEX ix_trip_company_responses_company ON partner.trip_company_responses USING btree (organization_id, share_id, created_at DESC)`
- `ix_trip_company_responses_traveler`: `CREATE INDEX ix_trip_company_responses_traveler ON partner.trip_company_responses USING btree (traveler_id, trip_id, created_at DESC)`
- `trip_company_responses_pkey`: `CREATE UNIQUE INDEX trip_company_responses_pkey ON partner.trip_company_responses USING btree (response_id)`
- `trip_company_responses_share_id_client_request_id_key`: `CREATE UNIQUE INDEX trip_company_responses_share_id_client_request_id_key ON partner.trip_company_responses USING btree (share_id, client_request_id)`

## سیاست‌های RLS

- `trip_company_responses_decide`: command=w, roles=[], using=`(traveler_id = partner.current_actor_id())`, with_check=`(traveler_id = partner.current_actor_id())`
- `trip_company_responses_insert`: command=a, roles=[], using=`—`, with_check=`((submitted_by = partner.current_actor_id()) AND (NOT is_synthetic) AND (EXISTS ( SELECT 1    FROM partner.traveler_request_shares s   WHERE ((s.share_id = trip_company_responses.share_id) AND (s.trip_id = trip_company_responses.trip_id) AND (s.traveler_id = trip_company_responses.traveler_id) AND (s.organization_id = trip_company_responses.organization_id) AND (s.revoked_at IS NULL) AND partner.has_active_membership(s.organization_id, partner.current_actor_id())))))`
- `trip_company_responses_read`: command=r, roles=[], using=`((traveler_id = partner.current_actor_id()) OR (EXISTS ( SELECT 1    FROM partner.traveler_request_shares s   WHERE ((s.share_id = trip_company_responses.share_id) AND (s.organization_id = trip_company_responses.organization_id) AND (s.revoked_at IS NULL) AND partner.has_active_membership(s.organization_id, partner.current_actor_id())))))`, with_check=`—`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **18**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
