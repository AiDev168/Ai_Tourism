# partner.traveler_request_shares

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** اشتراک‌گذاری موردی و رضایت‌مندانه درخواست یک سفر با یک سازمان.
- **دسترسی خواندن:** Trip owner or active organization members while share is not revoked.
- **دسترسی نوشتن:** Created only after explicit traveler consent; traveler may revoke.
- **نمایش عمومی:** Private, authenticated, tenant-scoped.
- **API مدل/مسیر:** POST/GET/DELETE /trips/{trip_id}/company-shares.
- **فیلد فرم UI:** Traveler journey company-sharing consent flow.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'share_id' | 'uuid' | خیر | 'gen_random_uuid()' | شناسه یکتای اشتراک‌گذاری. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'trip_id' | 'uuid' | خیر | — | سفر مبدا درخواست. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'traveler_id' | 'uuid' | خیر | — | مالک درخواست سفر. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'organization_id' | 'uuid' | خیر | — | سازمان دریافت‌کننده درخواست. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'consent_policy_version' | 'text' | خیر | — | نسخه قرارداد رضایت معتبر هنگام اشتراک‌گذاری. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'include_original_request' | 'boolean' | خیر | 'false' | مشخص می‌کند متن اولیه خام درخواست نیز با رضایت صریح ضمیمه شده یا خیر. | true / false |
| 'consented_at' | 'timestamp with time zone' | خیر | 'now()' | زمان اخذ رضایت و ایجاد دسترسی. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'revoked_at' | 'timestamp with time zone' | بله | — | زمان لغو دسترسی، در صورت وقوع. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp the explicit traveler-authorized share was created. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **traveler_request_shares_check** (`c`): `CHECK (((revoked_at IS NULL) OR (revoked_at >= consented_at)))`
- **traveler_request_shares_consent_policy_version_check** (`c`): `CHECK (((length(btrim(consent_policy_version)) >= 1) AND (length(btrim(consent_policy_version)) <= 80)))`
- **traveler_request_shares_organization_id_fkey** (`f`): `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- **traveler_request_shares_traveler_id_fkey** (`f`): `FOREIGN KEY (traveler_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- **traveler_request_shares_trip_id_fkey** (`f`): `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- **traveler_request_shares_pkey** (`p`): `PRIMARY KEY (share_id)`
- **traveler_request_shares_share_id_organization_id_key** (`u`): `UNIQUE (share_id, organization_id)`
- **traveler_request_shares_trip_id_organization_id_key** (`u`): `UNIQUE (trip_id, organization_id)`

## ایندکس‌ها

- `ix_traveler_request_shares_org`: `CREATE INDEX ix_traveler_request_shares_org ON partner.traveler_request_shares USING btree (organization_id, created_at DESC) WHERE (revoked_at IS NULL)`
- `ix_traveler_request_shares_owner`: `CREATE INDEX ix_traveler_request_shares_owner ON partner.traveler_request_shares USING btree (traveler_id, created_at DESC)`
- `traveler_request_shares_pkey`: `CREATE UNIQUE INDEX traveler_request_shares_pkey ON partner.traveler_request_shares USING btree (share_id)`
- `traveler_request_shares_share_id_organization_id_key`: `CREATE UNIQUE INDEX traveler_request_shares_share_id_organization_id_key ON partner.traveler_request_shares USING btree (share_id, organization_id)`
- `traveler_request_shares_trip_id_organization_id_key`: `CREATE UNIQUE INDEX traveler_request_shares_trip_id_organization_id_key ON partner.traveler_request_shares USING btree (trip_id, organization_id)`

## سیاست‌های RLS

- `traveler_share_insert`: command=a, roles=[], using=`—`, with_check=`((traveler_id = partner.current_actor_id()) AND (EXISTS ( SELECT 1    FROM travel.trips t   WHERE ((t.trip_id = traveler_request_shares.trip_id) AND (t.user_id = partner.current_actor_id()) AND (NOT t.is_synthetic)))) AND (EXISTS ( SELECT 1    FROM partner.share_eligible_organizations o   WHERE (o.organization_id = traveler_request_shares.organization_id))))`
- `traveler_share_read`: command=r, roles=[], using=`((traveler_id = partner.current_actor_id()) OR ((revoked_at IS NULL) AND partner.has_active_membership(organization_id, partner.current_actor_id())))`, with_check=`—`
- `traveler_share_revoke`: command=w, roles=[], using=`(traveler_id = partner.current_actor_id())`, with_check=`(traveler_id = partner.current_actor_id())`

## تریگرهای غیرسیستمی

- `trg_trip_request_revision_share`: `CREATE TRIGGER trg_trip_request_revision_share AFTER INSERT ON partner.traveler_request_shares FOR EACH ROW EXECUTE FUNCTION partner.capture_trip_request_revision_from_share()`

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **9**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
