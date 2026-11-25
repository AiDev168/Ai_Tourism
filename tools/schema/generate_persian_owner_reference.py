"""Generate a Persian owner index from the checked-in, sanitized schema manifest."""

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/database/live-schema/manifest.json"
OUTPUT = ROOT / "docs/database/OWNER_REFERENCE_FA.md"


def generate() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    groups: dict[str, list[dict]] = defaultdict(list)
    for relation in manifest["relations"]:
        groups[relation["schema"]].append(relation)

    lines = [
        "# راهنمای مالک برای فرم‌ها و مرجع پایگاه‌دادهٔ رهگرد",
        "",
        "> این فهرست از snapshot پالایش‌شدهٔ فقط‌خواندنیِ یک پایگاه‌داده ساخته شده است؛ آن را به‌عنوان موجودی کل VPS یا تأیید معماری تلقی نکنید.",
        "",
        f"- منبع تاریخی: `{manifest['database_observations'][0]['database']}`، PostgreSQL `{manifest['database_observations'][0]['database_identity']['server_version']}`، snapshot `{manifest['created_utc']}`.",
        f"- نسخهٔ برنامهٔ مشاهده‌شده: `{manifest['source_release']}`؛ snapshot live تا مهاجرت ۰۰۲۳ است و migrations ۰۰۲۴–۰۰۲۶ را شامل نمی‌شود.",
        f"- پوشش این snapshot: {len(manifest['relations'])} relation، از جمله viewها؛ تعداد descriptionهای glossary و occurrenceها را با تعداد پارامترهای منطقی محصول یکی نگیرید.",
        "- نسخهٔ ایزولهٔ rehearse‌شده: migrations ۰۰۲۴–۰۰۲۶ روی clone بازیابی‌شده اجرا شد. جدول‌های افزوده‌شده در این نسخه فقط در بخش «تغییرات rehearseشده» معرفی می‌شوند؛ زنده تلقی نمی‌شوند.",
        "",
        "## مسیرهای واقعی کاربر و پوشش فرم/API",
        "",
        "| نقش | فرم/مسیر در UI | جدول‌ها و viewهای اصلی | مسیر API/کد و حدود مجوز |",
        "|---|---|---|---|",
        "| مالک/بازبین پلتفرم | `/admin` در `frontend/src/admin/AdminControlCenter.tsx`؛ MFA در `PlatformAdminMfaPanel.tsx` | `partner.platform_grants`, `partner.review_events`, `partner.organizations`, `identity.catalogue_review_grants`, `knowledge.destination_candidates`, viewهای انتشار | `backend/app/api/admin.py`, `backend/app/api/partners.py`, `backend/app/api/platform_admin_mfa.py`; فقط مجوز صریح، step-up برای اقدام ممتاز و audit؛ AI-provider admin در VPS فعال نیست. |",
        "| نمایندهٔ شرکت | `/partners` در `frontend/src/partners/PartnerWorkspace.tsx` | `partner.organizations`, `memberships`, `services`, `service_destinations`, `schedules`, `offers`, `prices`, `availability_snapshots`, viewهای eligible/share | `backend/app/api/partners.py`; هر نوشتن در محدودهٔ سازمان عضو، RLS/authorization؛ فرم عمومی برای OTP، session، grant و audit وجود ندارد. |",
        "| مسافر | workspace مسافر در `frontend/src/trip/TravelerJourney.tsx` | `travel.trips`, `trip_constraints`, `trip_interests`, `trip_requirement_revisions`, `conversation.conversations/messages`, `travel.itineraries/stops`, share/revision tables | `backend/app/api/traveler.py`, `assistant.py`, `recommendations.py`, `partners.py`; مالکیت مسافر و رضایت جداگانه برای اشتراک با شرکت. |",
        "| اپراتور استقرار | shell/Compose، نه فرم عمومی | `system.schema_migrations`, `operations.*`, marker و role grants | اسکریپت‌های کنترل‌شدهٔ استقرار؛ هرگز از فرم عمومی یا API مسافر قابل‌نوشتن نیستند. |",
        "",
        "## پوشش فیلدها و محدودیت معنا",
        "",
        "- مرجع کامل occurrenceها: [ماتریس ستون‌ها](architecture-usage/column_occurrence_matrix.csv)، [lineage viewها](architecture-usage/view_column_lineage.csv)، [وابستگی API](architecture-usage/api_dependency_map.csv)، [تصمیم relationها](architecture-usage/object_decision_matrix.csv) و [گزارش معماری/مصرف](architecture-usage/ARCHITECTURE_AND_USAGE_REVIEW.md).",
        "- baseline تاریخی: ۱۰۱ relation، ۱٬۱۰۶ occurrence، ۲۳۰ description موجود و ۸۷۶ شکاف glossary. طبقه‌بندی شکاف‌ها: ۶۰۵ occurrence پایهٔ برنامه، ۱۰۲ سیستم/عملیات، ۱۵۰ view مشتق و ۱۹ PostGIS. ۸۷۶ نیاز تازهٔ کسب‌وکار نیست.",
        "- تصمیم relationها: ۶۱ KEEP، ۳۷ INVESTIGATE، ۳ EXTENSION-MANAGED. این وضعیت‌ها حفاظت/تحقیق را نشان می‌دهند، نه تأیید نهایی ضرورت معماری.",
        "- هر فیلد بدون شاهد در `field_descriptions.json` صریحاً نامشخص می‌ماند. برای viewها به expression مبدأ ارجاع دهید؛ برای PostGIS به مستندات رسمی extension؛ نام یا نوع SQL به‌تنهایی معنای محصول را ثابت نمی‌کند.",
        "- فرق فرم‌پذیر با خودکار/سیستمی: اطلاعات پایهٔ سازمان، خدمت، برنامه و قیمت فقط از فرم/API tenant مجاز نوشته می‌شوند؛ session، OTP، محدودیت نرخ، مهاجرت، grant و audit فقط سامانه/اپراتور کنترل‌شده را دارند.",
        "",
        "## تغییرات rehearseشدهٔ ۰۰۲۴–۰۰۲۶ (فقط clone ایزوله)",
        "",
        "- ۰۰۲۴: تغییر مجاز vocabulary و policy درج در `partner.review_events`; بدون grant بازبین و بدون تغییر دادهٔ موجود.",
        "- ۰۰۲۵: افزودن `partner.platform_grant_events` و تابع تجمیع شمار مجوز؛ check constraint grant توسعه یافت.",
        "- ۰۰۲۶: افزودن `identity.platform_admin_mfa`, `identity.platform_admin_step_up`, `identity.platform_admin_mfa_events`، policyهای RLS و توابع audit/capability. هیچ حساب بازبین یا MFA secret در clone ساخته نشد.",
        "- شاهد دقیق: [بازیابی و rehearsal](../operations/evidence/issue27/R4-restore-migrations-2026-11-25.json) و [تغییرات ستون‌های ۰۰۲۴–۰۰۲۶](REHEARSED_0024_0026_FIELD_REFERENCE.md). این اسناد schema زنده را تغییر نمی‌دهند.",
        "",
        "## فهرست همهٔ relationهای snapshot با پیوند به سند جزئی",
        "",
    ]
    for schema in sorted(groups):
        lines.extend([f"### `{schema}`", ""])
        for relation in sorted(groups[schema], key=lambda item: item["name"]):
            # The manifest path is authoritative and includes its stable hashes.
            link = "live-schema/" + relation["path"]
            description = f"{relation['columns']} occurrence"
            if relation.get("undocumented_columns"):
                description += f"؛ {relation['undocumented_columns']} بدون شرح baseline"
            lines.append(f"- [`{relation['name']}`]({link}) — {description}; {relation['kind']}.")
        lines.append("")
    lines.extend([
        "## تغییر وضعیت پس از rehearse تا production",
        "",
        "در snapshot آخرِ فقط‌خواندنی، VPS هنوز ledger تا ۰۰۲۳ داشت؛ clone rehearsal تا ۰۰۲۶ رفت. DDL، secrets، grants، داده یا سرویس live در این ماموریت تغییر نکرده‌اند. برای تغییر live به مجوز جداگانهٔ دقیق نیاز است.",
        "",
    ])
    OUTPUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    generate()
