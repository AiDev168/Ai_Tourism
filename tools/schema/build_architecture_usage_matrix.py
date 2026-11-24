#!/usr/bin/env python3
"""Build evidence-linked, occurrence-aware Rahgard schema usage matrices.

This tool reads only the sanitized catalog snapshot, checked-in source files,
the baseline glossary, and a short-lived metadata-only catalog extract of
relation owners/view definitions. It never connects to PostgreSQL and never
reads application rows. Static text matches are explicitly labeled as leads,
not proof that a code path executes.
"""
from __future__ import annotations

import csv
import ast
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "docs/database/live-schema/catalog_snapshot.json"
LIVE_METADATA = ROOT / "docs/database/live-schema/catalog_metadata_snapshot.json"
GLOSSARY = ROOT / "docs/database/field_descriptions.json"
OUTPUT = ROOT / "docs/database/architecture-usage"
EXTENSION_OBJECTS = {
    ("public", "spatial_ref_sys"),
    ("public", "geometry_columns"),
    ("public", "geography_columns"),
}
SCHEMA_STEWARDS = {
    "knowledge": ("catalogue and evidence", "backend/app/api/catalogue.py; backend/app/api/catalogue_review.py; engineering/database-prep/sql"),
    "partner": ("company workspace and review", "backend/app/api/partners.py; backend/app/api/partner_review.py; frontend/src/partners"),
    "travel": ("traveler requirements and itinerary", "backend/app/api/traveler.py; backend/app/modules/trip; frontend/src/trip"),
    "identity": ("authentication and traveler identity", "backend/app/api/auth.py; backend/app/modules/identity"),
    "conversation": ("conversation and assistant turns", "backend/app/api/assistant.py; backend/app/modules/trip/assistant_turns.py"),
    "geo": ("administrative geography", "backend/app/modules/geo; engineering/pilot/sql"),
    "recommendation": ("recommendation requests and results", "backend/app/modules/recommendation; backend/app/api/traveler.py"),
    "integration": ("external links and AI integration budgets", "backend/app/modules/integrations; backend/app/api"),
    "operations": ("audit, imports, diagnostics and usage", "backend/app/modules; backend/app/api"),
    "system": ("migration ledger and database operations", "engineering/database-prep/sql/000_bootstrap.sql; deployment tooling"),
    "public": ("mixed: pilot marker and PostGIS-managed catalog objects", "engineering/pilot/sql; PostGIS extension"),
}
SCHEMA_UI_SURFACES = {
    "knowledge": "frontend/src/trip/destinationCatalogApi.ts; frontend/src/admin/catalogue/CatalogueReviewPanel.tsx",
    "partner": "frontend/src/partners/PartnerWorkspace.tsx; frontend/src/partners/CompanyResponseActions.tsx",
    "travel": "frontend/src/trip/TravelerJourney.tsx; frontend/src/trip/travelerApi.ts",
    "identity": "frontend/src/auth/AuthPanel.tsx; frontend/src/auth/travelerAuthApi.ts",
    "conversation": "frontend/src/trip/TravelerJourney.tsx; frontend/src/trip/travelerApi.ts",
    "geo": "frontend/src/trip/TravelerJourney.tsx; frontend/src/trip/JalaliDatePicker.tsx (domain-level UI, no direct DB access)",
    "recommendation": "frontend/src/trip/TravelerJourney.tsx; frontend/src/trip/travelerApi.ts",
    "integration": "frontend/src/trip/TravelerJourney.tsx; frontend/src/admin/ai-providers (if route enabled)",
    "operations": "no ordinary traveler/company form; operator surface must be confirmed per relation",
    "system": "deployment tooling only; no user form",
    "public": "PostGIS metadata is not a Rahgard form; pilot marker is operator-managed",
}
SOURCE_SUFFIXES = {".py", ".sql", ".tsx", ".ts", ".jsx", ".js"}
SKIP_PARTS = {"node_modules", ".venv", "dist", "build", ".git"}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_sources() -> list[tuple[str, str]]:
    roots = [ROOT / "backend/app", ROOT / "backend/tests", ROOT / "frontend/src", ROOT / "engineering", ROOT / "scripts"]
    found: list[tuple[str, str]] = []
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix.lower() not in SOURCE_SUFFIXES or any(x in SKIP_PARTS for x in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            found.append((path.relative_to(ROOT).as_posix(), text))
    return found


def ddl_provenance(sources: list[tuple[str, str]]) -> dict[tuple[str, str], list[str]]:
    pattern = re.compile(
        r"\b(?:CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW|MATERIALIZED\s+VIEW|FOREIGN\s+TABLE)"
        r"\s+(?:IF\s+NOT\s+EXISTS\s+)?)([\w\"]+)\.([\w\"]+)", re.I
    )
    result: dict[tuple[str, str], list[str]] = defaultdict(list)
    for path, text in sources:
        if not path.endswith(".sql"):
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            match = pattern.search(line)
            if match:
                schema, relation = (x.strip('"').lower() for x in match.groups())
                result[(schema, relation)].append(f"{path}:{line_no}")
    return result


def ddl_touchpoints(sources: list[tuple[str, str]], schema: str, relation: str) -> list[str]:
    """Collect migration SQL lines mentioning an object; classified as leads, not parsed semantics."""
    pattern = re.compile(rf"(?<![\w]){re.escape(schema)}\s*\.\s*{re.escape(relation)}(?![\w])", re.I)
    hits = []
    for path, text in sources:
        if not path.endswith(".sql"):
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                hits.append(f"{path}:{line_no}")
    return hits


def static_relation_refs(indexes: dict, schema: str, relation: str) -> dict[str, list[str]]:
    paths = indexes.get((schema.lower(), relation.lower()), set())
    buckets: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        if path.startswith("backend/app/"):
            bucket = "backend/app"
        elif path.startswith("frontend/src/"):
            bucket = "frontend/src"
        elif "/tests/" in path or path.startswith("backend/tests/"):
            bucket = "tests"
        elif path.endswith(".sql"):
            bucket = "sql_or_migration"
        else:
            bucket = "scripts_or_docs"
        buckets[bucket].append(path)
    return {k: sorted(set(v)) for k, v in buckets.items()}


def field_hits(indexes: dict, name: str) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = defaultdict(list)
    for path in indexes.get(name.lower(), set()):
        if path.startswith("backend/app/"):
            buckets["backend/app"].append(path)
        elif path.startswith("frontend/src/"):
            buckets["frontend/src"].append(path)
        elif "/tests/" in path or path.startswith("backend/tests/"):
            buckets["tests"].append(path)
        elif path.endswith(".sql"):
            buckets["sql_or_migration"].append(path)
        else:
            buckets["scripts_or_docs"].append(path)
    return {k: sorted(set(v)) for k, v in buckets.items()}


def static_sql_operation_hints(text: str, schema: str, relation: str, line_offset: int = 0) -> list[str]:
    """Find explicit qualified CRUD clauses; hints only, not runtime proof."""
    qualified = rf"(?<![\w]){re.escape(schema)}\s*\.\s*{re.escape(relation)}(?![\w])"
    clauses = {
        "INSERT": rf"\bINSERT\s+INTO\s+{qualified}",
        "UPDATE": rf"\bUPDATE\s+{qualified}",
        "DELETE": rf"\bDELETE\s+FROM\s+{qualified}",
        "SELECT": rf"\bFROM\s+{qualified}",
        "JOIN": rf"\bJOIN\s+{qualified}",
        "MERGE": rf"\bMERGE\s+INTO\s+{qualified}",
    }
    found = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for operation, pattern in clauses.items():
            if re.search(pattern, line, re.I):
                found.append(f"{operation}@{line_no + line_offset}")
    return sorted(set(found))


def build_source_indexes(sources: list[tuple[str, str]]) -> tuple[dict, dict]:
    """Index identifiers and qualified pairs in one pass instead of rescanning source per field."""
    field_index: dict[str, set[str]] = defaultdict(set)
    relation_index: dict[tuple[str, str], set[str]] = defaultdict(set)
    identifiers = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z_][A-Za-z0-9_]*(?![A-Za-z0-9_])")
    qualified = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)(?![A-Za-z0-9_])")
    for path, text in sources:
        for match in identifiers.finditer(text):
            field_index[match.group(0).lower()].add(path)
        for match in qualified.finditer(text):
            relation_index[(match.group(1).lower(), match.group(2).lower())].add(path)
    return field_index, relation_index


def decision_for(schema: str, name: str, kind: str, refs: dict[str, list[str]], ddl: list[str]) -> tuple[str, str]:
    if (schema, name) in EXTENSION_OBJECTS:
        return "EXTENSION-MANAGED", "PostGIS-owned technical catalog object; keep under extension lifecycle, not a Rahgard business form."
    if kind in {"v", "m"}:
        if refs.get("backend/app") or refs.get("frontend/src"):
            return "KEEP", "Derived read boundary has an application source reference; retain publication/filter semantics and review changes additively."
        return "INVESTIGATE", "Derived view has no literal application reference in the scanned source; static search is incomplete evidence, so do not remove."
    if schema == "system":
        return "KEEP", "Migration/system ledger is needed for deployment and schema-state safety."
    if refs.get("backend/app") or refs.get("frontend/src"):
        return "KEEP", "Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary."
    if not ddl:
        return "INVESTIGATE", "No checked-in CREATE statement was found in the scanned SQL; owner/provenance must be confirmed before any change."
    return "INVESTIGATE", "No qualified backend/frontend relation reference was found; dynamic queries, contracts, or compatibility use may exist. Preserve until confirmed."


def sensitivity(schema: str, column: str, owner: str) -> tuple[str, str]:
    name = column.lower()
    if (schema, "spatial_ref_sys") in EXTENSION_OBJECTS or owner == "extension":
        return "technical_extension_metadata", "PostGIS object classification; not traveler/company data."
    if re.search(r"password|token|secret|csrf|otp|salt|verifier|credential|session|api_key|private_key", name):
        return "restricted_auth_or_secret_metadata", "Column name and identity/provider contract; values must never be exposed in documentation."
    if schema in {"identity", "conversation", "travel", "recommendation"}:
        return "traveler_private", "Owning domain contains identity, trip, conversation, or personalized recommendation state."
    if schema == "partner":
        return "tenant_private_until_reviewed", "Partner tenant data; publication requires independent review/eligibility policy."
    if schema == "knowledge":
        return "editorial_private_or_public_after_publication", "Knowledge/catalogue provenance and publication view govern exposure."
    if schema in {"operations", "system", "integration"}:
        return "restricted_operational_metadata", "Operational, integration, audit, or migration surface; not a public content contract."
    if schema == "geo":
        return "administrative_geography_metadata", "Administrative reference data; source release and publication context still apply."
    return "technical_metadata_review", "Classification is provisional; validate against the owning contract before exposing values."


def split_select(sql: str) -> list[str]:
    """Split the outermost view SELECT list; skip nested CTE/subquery SELECTs."""
    depth = 0
    quote: str | None = None
    start: int | None = None
    i = 0
    while i < len(sql):
        ch = sql[i]
        if quote:
            if ch == quote:
                if i + 1 < len(sql) and sql[i + 1] == quote:
                    i += 2
                    continue
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0 and start is None and re.match(r"SELECT\b", sql[i:], re.I):
            start = i + len("SELECT")
            i = start
            continue
        elif (depth == 0 and start is not None
              and re.match(r"FROM\b", sql[i:], re.I)
              and (i == 0 or not (sql[i - 1].isalnum() or sql[i - 1] == "_"))):
            prefix = sql[max(0, i - 32):i]
            # `IS [NOT] DISTINCT FROM` is an expression operator, not the
            # SELECT/FROM clause boundary.
            if re.search(r"\bIS\s+(?:NOT\s+)?DISTINCT\s+$", prefix, re.I):
                i += len("FROM")
                continue
            return split_commas(sql[start:i])
        i += 1
    return []


def top_level_from_position(sql: str) -> int | None:
    depth, quote, i = 0, None, 0
    while i < len(sql):
        ch = sql[i]
        if quote:
            if ch == quote:
                if i + 1 < len(sql) and sql[i + 1] == quote:
                    i += 2
                    continue
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif (depth == 0 and re.match(r"FROM\b", sql[i:], re.I)
              and (i == 0 or not (sql[i - 1].isalnum() or sql[i - 1] == "_"))):
            prefix = sql[max(0, i - 32):i]
            if re.search(r"\bIS\s+(?:NOT\s+)?DISTINCT\s+$", prefix, re.I):
                i += len("FROM")
                continue
            return i
        i += 1
    return None


def split_commas(text: str) -> list[str]:
    result, start, depth, quote, i = [], 0, 0, None, 0
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == quote:
                if i + 1 < len(text) and text[i + 1] == quote:
                    i += 2
                    continue
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            result.append(text[start:i].strip())
            start = i + 1
        i += 1
    tail = text[start:].strip()
    if tail:
        result.append(tail)
    return result


def parse_view_lineage(sql: str | None, output_columns: list[dict], snapshot: dict) -> dict[str, tuple[str, str]]:
    if not sql:
        return {}
    projections = split_select(sql)
    aliases: dict[str, tuple[str, str]] = {}
    rel_by_name = {(x["relation"]["schema"], x["relation"]["name"]): x for x in snapshot["relations"]}
    from_pos = top_level_from_position(sql)
    from_clause = sql[from_pos:] if from_pos is not None else ""
    clause_depth, quote, clause_end = 0, None, len(from_clause)
    for index, ch in enumerate(from_clause):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "(":
            clause_depth += 1
        elif ch == ")":
            clause_depth -= 1
        elif clause_depth == 0 and re.match(r"WHERE\b", from_clause[index:], re.I):
            clause_end = index
            break
    for match in re.finditer(r"\b(?:FROM|JOIN)\s+([\w.]+)(?:\s+(?:AS\s+)?([A-Za-z_]\w*))?", from_clause[:clause_end], re.I):
        qualified_name, explicit_alias = match.groups()
        if "." not in qualified_name:
            continue
        source_schema, source_name = qualified_name.split(".", 1)
        alias = explicit_alias or source_name
        # SQL keywords following a relation without an explicit alias are not aliases.
        if alias.lower() in {"where", "join", "left", "right", "inner", "outer", "full", "on", "group", "order", "limit", "union"}:
            alias = source_name
        if (source_schema, source_name) in rel_by_name:
            aliases[alias] = (source_schema, source_name)
    expanded: list[str] = []
    for projection in projections:
        star = re.fullmatch(r"([A-Za-z_]\w*)\.\*", projection.strip())
        if star and star.group(1) in aliases:
            source_schema, source_name = aliases[star.group(1)]
            source_relation = rel_by_name[(source_schema, source_name)]
            expanded.extend([f"{star.group(1)}.{column['name']}" for column in source_relation["columns"]])
        else:
            expanded.append(projection)
    projections = expanded
    if len(projections) == 1 and re.fullmatch(r"\w+\.\*", projections[0]):
        alias = projections[0][:-2]
        frm = re.search(rf"\bFROM\s+([\w.]+)\s+(?:AS\s+)?{re.escape(alias)}\b", sql, re.I)
        if frm:
            schema, rel = frm.group(1).split(".", 1)
            source = next((x for x in snapshot["relations"] if (x["relation"]["schema"], x["relation"]["name"]) == (schema, rel)), None)
            if source and len(source["columns"]) == len(output_columns):
                return {out["name"]: (f"{schema}.{rel}.{base['name']}", "direct_star_projection")
                        for out, base in zip(output_columns, source["columns"])}
    result = {}
    if len(projections) != len(output_columns):
        return {c["name"]: ("", "projection_count_mismatch_needs_review") for c in output_columns}
    for col, expr in zip(output_columns, projections):
        alias_match = re.search(r"\s+AS\s+([\w\"]+)$", expr, re.I)
        expression = expr[:alias_match.start()].strip() if alias_match else expr
        refs = re.findall(r"\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\b", expression)
        status = "source_expression"
        if len(refs) == 1 and re.fullmatch(r"\s*[A-Za-z_]\w*\.[A-Za-z_]\w*\s*", expression):
            status = "direct_column_projection"
        elif not refs:
            bare = re.fullmatch(r"\s*([A-Za-z_]\w*)\s*", expression)
            if bare:
                source_col = bare.group(1)
                candidates = [(schema, relation) for schema, relation in aliases.values()
                              if any(c["name"] == source_col for c in rel_by_name[(schema, relation)]["columns"])]
                if len(set(candidates)) == 1:
                    refs = [(next(alias for alias, target in aliases.items() if target == candidates[0]), source_col)]
                    status = "direct_unqualified_column_unique_source"
                elif candidates:
                    status = "ambiguous_unqualified_column"
                else:
                    status = "constant_or_unqualified_expression_needs_review"
            elif re.match(r"\s*current_database\s*\(\)", expression, re.I):
                status = "database_context_expression"
            else:
                status = "constant_or_unqualified_expression_needs_review"
        mapped_refs = [f"{aliases[a][0]}.{aliases[a][1]}.{c}" if a in aliases else f"{a}.{c}" for a, c in refs]
        source_expression = f"{expression} [inputs: {', '.join(mapped_refs)}]" if mapped_refs else expression
        result[col["name"]] = (source_expression, status)
    return result


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    snapshot = load_json(SNAPSHOT)
    live = load_json(LIVE_METADATA)
    if (live.get("database") != "rahgard_pilot_vps_staging" or live.get("role") != "ai_tourism_app"
            or snapshot.get("database_identity", {}).get("database") != live.get("database")):
        raise SystemExit("refusing metadata with unexpected database identity")
    live_objects = {(x["schema"], x["name"]): x for x in live["objects"]}
    expected_objects = {(item["relation"]["schema"], item["relation"]["name"])
                        for item in snapshot["relations"]}
    if set(live_objects) != expected_objects:
        raise SystemExit("captured relation metadata identities differ from sanitized snapshot")
    sources = read_sources()
    ddl = ddl_provenance(sources)
    field_index, relation_index = build_source_indexes(sources)
    baseline = load_json(GLOSSARY)
    objects, columns, lineage_rows = [], [], []
    counter = Counter()
    by_schema = defaultdict(lambda: Counter())
    for rel in snapshot["relations"]:
        schema, name, kind = rel["relation"]["schema"], rel["relation"]["name"], rel["relation"]["kind"]
        key = (schema, name)
        live_obj = live_objects.get(key, {})
        obj_owner = live_obj.get("database_owner", live_obj.get("owner", "not captured"))
        is_extension = key in EXTENSION_OBJECTS
        origin = ("extension_managed" if is_extension else
                  "derived_view" if kind in {"v", "m"} else
                  "first_party_system_or_operations" if schema in {"system", "operations", "integration"} or (schema, name) == ("public", "rahgard_private_pilot_marker") else
                  "first_party_application_base")
        rel_refs = static_relation_refs(relation_index, schema, name)
        prov = ddl.get(key, [])
        touchpoints = ddl_touchpoints(sources, schema, name)
        operation_evidence = []
        for source_path, source_text in sources:
            if not source_path.startswith("backend/app/") or not source_path.endswith(".py"):
                continue
            operation_evidence.extend(f"{source_path}:{hint}" for hint in static_sql_operation_hints(source_text, schema, name))
        decision, rationale = decision_for(schema, name, kind, rel_refs, prov)
        stewardship, steward_evidence = SCHEMA_STEWARDS.get(schema, ("unassigned", "no mapped source owner"))
        fks = []
        for c in rel.get("constraints", []):
            if c.get("type") == "f":
                fks.append(f"{c['name']}: {c['definition']}")
        all_incoming = []
        for other in snapshot["relations"]:
            for c in other.get("constraints", []):
                if c.get("type") == "f" and re.search(rf"REFERENCES\s+{re.escape(schema)}\.{re.escape(name)}\b", c.get("definition", ""), re.I):
                    all_incoming.append(f"{other['relation']['schema']}.{other['relation']['name']}:{c['name']}")
        policy = (
            "PostGIS extension metadata; not a public Rahgard feature"
            if is_extension else
            "Publication-filtered derived view; inspect view SQL and owning API before changing"
            if kind in {"v", "m"} and schema == "knowledge" and name.startswith("production_") else
            "Share-eligibility projection; consent and reviewer state gate exposure"
            if (schema, name) == ("partner", "share_eligible_organizations") else
            "Private by default; public use only through a separate approved publication path"
            if schema in {"knowledge", "partner"} else
            "Protected application data; API/RLS/grants determine caller access"
        )
        objects.append({
            "database": rel["database"], "schema": schema, "relation": name,
            "kind": {"r":"table", "p":"partitioned_table", "v":"view", "m":"materialized_view", "f":"foreign_table"}.get(kind, kind),
            "column_occurrences": len(rel["columns"]), "origin_class": origin,
            "ddl_provenance": "; ".join(prov) if prov else "not found in scanned checked-in SQL",
            "migration_ddl_touchpoints": "; ".join(touchpoints) or "none found in scanned SQL",
            "database_owner": obj_owner, "technical_steward": stewardship,
            "stewardship_evidence": steward_evidence,
            "data_row_origin_assessment": "not assessed; no application rows were read; import/synthetic/legacy population must be checked through separately authorized row-level status fields",
            "outgoing_fk_edges": " | ".join(fks) or "none recorded",
            "incoming_fk_edges": " | ".join(sorted(all_incoming)) or "none recorded",
            "backend_relation_refs": " | ".join(rel_refs.get("backend/app", [])) or "no literal qualified hit",
            "static_sql_operation_hints": " | ".join(operation_evidence) or "no explicit qualified CRUD clause found; not proof of no read/write path",
            "frontend_relation_refs": " | ".join(rel_refs.get("frontend/src", [])) or "no literal qualified hit",
            "domain_ui_surface_candidates": SCHEMA_UI_SURFACES.get(schema, "not mapped"),
            "test_refs": " | ".join(rel_refs.get("tests", [])) or "no literal qualified hit",
            "publication_policy_evidence": policy,
            "decision": decision, "decision_rationale": rationale,
            "risk_if_changed": "HIGH: existing persistent data and compatibility may depend on this object; no destructive action approved",
        })
        counter[(origin, decision)] += 1
        by_schema[schema][origin] += 1
        lineage = parse_view_lineage(live_obj.get("view_sql"), rel["columns"], snapshot) if kind in {"v", "m"} else {}
        for col in rel["columns"]:
            field_name = col["name"]
            existing = baseline.get(f"{schema}.{name}", {}).get(field_name)
            known_glossary = isinstance(existing, str) and bool(existing.strip())
            sens, sens_basis = sensitivity(schema, field_name, "extension" if is_extension else "application")
            expr, lineage_status = lineage.get(field_name, ("", "not_a_derived_view_column"))
            hits = field_hits(field_index, field_name)
            if is_extension:
                desc_status = "official_extension_reference"
            elif kind in {"v", "m"}:
                desc_status = "derived_occurrence_lineage_only" if expr else "derived_occurrence_lineage_unresolved"
            else:
                desc_status = "existing_glossary_entry" if known_glossary else "undocumented_occurrence"
            columns.append({
                "database": rel["database"], "schema": schema, "relation": name,
                "relation_kind": kind, "origin_class": origin, "column_name": field_name,
                "pg_type": col["pg_type"], "nullable": not col["notnull"],
                "default_sql_sanitized": col.get("default") or "none",
                "constraint_evidence": " | ".join(c["name"] + ":" + c["definition"] for c in rel.get("constraints", []) if field_name in c.get("definition", "")) or "none identified by name; inspect object constraints",
                "glossary_status": desc_status,
                "baseline_glossary_meaning": existing if known_glossary else "",
                "view_source_expression": expr,
                "view_lineage_status": lineage_status,
                "source_evidence": (f"https://postgis.net/docs/using_postgis_dbmanagement.html; live read-only pg_get_viewdef sha256={hashlib.sha256((live_obj.get('view_sql') or '').encode()).hexdigest()}; source expression in view_column_lineage.csv"
                                    if is_extension and kind in {"v", "m"} else
                                    f"live read-only pg_get_viewdef sha256={hashlib.sha256((live_obj.get('view_sql') or '').encode()).hexdigest()}; source expression in view_column_lineage.csv"
                                    if kind in {"v", "m"} else
                                    "https://postgis.net/docs/using_postgis_dbmanagement.html" if is_extension else
                                    "; ".join(prov) if prov else "DDL source not found in scanned SQL; review migrations/extension setup"),
                "database_owner": obj_owner,
                "technical_steward": stewardship,
                "technical_steward_evidence": steward_evidence,
                "sensitivity_class": sens,
                "sensitivity_basis": sens_basis + "; provisional domain classification, not privacy-owner sign-off",
                "backend_field_token_hits": " | ".join(hits.get("backend/app", [])) or "none",
                "frontend_field_token_hits": " | ".join(hits.get("frontend/src", [])) or "none",
                "field_hit_limit": "Lexical token hits only; not proof of runtime field read/write or UI form ownership.",
                "necessity_status": "derived_projection_not_independent_attribute" if kind in {"v", "m"} else "not_independently_assessed",
            })
            by_schema[schema][desc_status] += 1
            if kind in {"v", "m"}:
                lineage_rows.append({"database": rel["database"], "view": f"{schema}.{name}", "output_column": field_name,
                                     "pg_type": col["pg_type"], "source_expression": expr,
                                     "lineage_status": lineage_status,
                                     "view_definition_sha256": hashlib.sha256((live_obj.get("view_sql") or "").encode()).hexdigest()})
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT / "object_decision_matrix.csv", objects, list(objects[0]))
    write_csv(OUTPUT / "column_occurrence_matrix.csv", columns, list(columns[0]))
    write_csv(OUTPUT / "view_column_lineage.csv", lineage_rows, list(lineage_rows[0]))
    fk_rows = []
    for rel in snapshot["relations"]:
        for constraint in rel.get("constraints", []):
            if constraint.get("type") == "f":
                target = re.search(r"REFERENCES\s+([\w.]+)\s*\(([^)]+)\)", constraint.get("definition", ""), re.I)
                fk_rows.append({"source_relation": f"{rel['relation']['schema']}.{rel['relation']['name']}",
                                "constraint": constraint["name"], "definition": constraint["definition"],
                                "target_relation": target.group(1) if target else "unparsed; see definition",
                                "target_columns": target.group(2) if target else "", "evidence": "live pg_catalog FK definition; read-only"})
    write_csv(OUTPUT / "foreign_key_edges.csv", fk_rows,
              ["source_relation", "constraint", "definition", "target_relation", "target_columns", "evidence"])
    api_rows = []
    for path, text in sources:
        if not path.startswith("backend/app/") or not path.endswith(".py"):
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            segment = ast.get_source_segment(text, node) or ""
            for obj in objects:
                token = f"{obj['schema']}.{obj['relation']}"
                if not re.search(re.escape(token), segment, re.I):
                    continue
                decorators = [ast.get_source_segment(text, dec) or "" for dec in node.decorator_list]
                route_decorators = [re.sub(r"\s+", " ", dec).strip() for dec in decorators
                                    if re.search(r"@\w+\.(?:get|post|put|patch|delete)\b", dec, re.I)]
                api_rows.append({"relation": token, "backend_module": path, "function": node.name,
                                 "route_decorators_in_same_function": " | ".join(route_decorators) or "none; internal helper/repository",
                                 "evidence": "qualified relation literal occurs in function source; static mapping only",
                                 "sql_operation_hints": "; ".join(static_sql_operation_hints(segment, obj["schema"], obj["relation"], node.lineno - 1)) or "no explicit qualified CRUD clause identified",
                                 "domain_ui_surface_candidates": obj["domain_ui_surface_candidates"]})
    api_relations = {row["relation"] for row in api_rows}
    for obj in objects:
        token = f"{obj['schema']}.{obj['relation']}"
        if token not in api_relations:
            api_rows.append({"relation": token, "backend_module": "", "function": "no qualified backend/app function literal found",
                             "route_decorators_in_same_function": "", "evidence": "absence of literal match is inconclusive; inspect repository abstractions/dynamic SQL",
                             "sql_operation_hints": "not identified by static scan",
                             "domain_ui_surface_candidates": obj["domain_ui_surface_candidates"]})
    write_csv(OUTPUT / "api_dependency_map.csv", api_rows,
              ["relation", "backend_module", "function", "route_decorators_in_same_function", "sql_operation_hints", "evidence", "domain_ui_surface_candidates"])
    coverage_rows = []
    schema_groups = sorted({x["schema"] for x in columns})
    for schema in schema_groups:
        values = [x for x in columns if x["schema"] == schema]
        by_origin = Counter(x["origin_class"] for x in values)
        by_status = Counter(x["glossary_status"] for x in values)
        documented = sum(1 for x in values if x["baseline_glossary_meaning"])
        coverage_rows.append({"schema": schema, "column_occurrences": len(values),
                              "first_party_application_base": by_origin["first_party_application_base"],
                              "first_party_system_or_operations": by_origin["first_party_system_or_operations"],
                              "derived_view_occurrences": by_origin["derived_view"],
                              "extension_managed_occurrences": by_origin["extension_managed"],
                              "baseline_glossary_entries": documented,
                              "undocumented_column_occurrences": len(values) - documented,
                              "undocumented_base_occurrences": by_status["undocumented_occurrence"],
                              "derived_lineage_occurrences": by_status["derived_occurrence_lineage_only"] + by_status["derived_occurrence_lineage_unresolved"],
                              "official_extension_reference_occurrences": by_status["official_extension_reference"]})
    write_csv(OUTPUT / "coverage_by_schema.csv", coverage_rows, list(coverage_rows[0]))
    summary = [
        "# Rahgard schema architecture and usage matrix - 2026-11-24", "",
        "## Scope and interpretation", "",
        f"This is a metadata/source-code audit of one authorized PostgreSQL database, not a claim that every physical column is a distinct business requirement. No application rows were read. Relation owner and view definitions came from `{LIVE_METADATA.relative_to(ROOT).as_posix()}` as read-only catalog metadata; SQL definitions are metadata only.", "",
        f"Database: `{snapshot['database_identity']['database']}`; role: `{snapshot['database_role']}`; server: `{snapshot['database_identity']['server_version']}`.",
        f"Objects: **{len(objects)}** ({sum(1 for x in objects if x['kind'] in {'table','partitioned_table'})} tables, {sum(1 for x in objects if x['kind'] in {'view','materialized_view'})} views); column occurrences: **{len(columns)}**; view output occurrences with SQL lineage records: **{len(lineage_rows)}** (including first-party projections and PostGIS extension views).",
        "The CSVs preserve unknowns. A static token match does not prove runtime use; absence of a match does not prove dead code. No migration, data change, or drop recommendation is made.", "",
        "## Object decisions", "",
        "Decision meanings: `KEEP` = observed code/required safety dependency; `CONSOLIDATE-LATER` = not assigned without demonstrated duplicate semantics; `LEGACY-COMPAT` = not assigned absent direct legacy evidence; `EXTENSION-MANAGED` = lifecycle owned by PostgreSQL/PostGIS; `INVESTIGATE` = no adequate evidence for an architectural necessity claim. These are preserve/review decisions, not schema approval.", "",
        "| Decision | Objects |", "|---|---:|",
    ]
    decisions = Counter(x["decision"] for x in objects)
    for decision in ["KEEP", "CONSOLIDATE-LATER", "LEGACY-COMPAT", "EXTENSION-MANAGED", "INVESTIGATE"]:
        summary.append(f"| {decision} | {decisions[decision]} |")
    summary += ["", "## Per-schema object and column occurrence counts", "",
                "| Schema | Objects | Tables | Views | Column occurrences | Existing glossary | Undocumented occurrences | Base-table undocumented | Derived view occurrences | Extension occurrences |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in coverage_rows:
        obj_group = [x for x in objects if x["schema"] == row["schema"]]
        summary.append(f"| {row['schema']} | {len(obj_group)} | {sum(1 for x in obj_group if x['kind'] in {'table','partitioned_table'})} | {sum(1 for x in obj_group if x['kind'] in {'view','materialized_view'})} | {row['column_occurrences']} | {row['baseline_glossary_entries']} | {row['undocumented_column_occurrences']} | {row['undocumented_base_occurrences']} | {row['derived_view_occurrences']} | {row['extension_managed_occurrences']} |")
    total_glossary = sum(row["baseline_glossary_entries"] for row in coverage_rows)
    total_missing = sum(row["column_occurrences"] for row in coverage_rows) - total_glossary
    summary += ["", f"Across this database snapshot, the baseline glossary has **{total_glossary}** matched column descriptions and **{total_missing}** undocumented column occurrences (the sum includes derived-view and extension occurrences). These are occurrence counts, not distinct parameters or validated requirements.", ""]
    origin_gaps = Counter()
    origin_described = Counter()
    for row in columns:
        origin = row["origin_class"]
        (origin_described if row["baseline_glossary_meaning"] else origin_gaps)[origin] += 1
    summary += ["### Glossary coverage by occurrence class", "",
                "| Occurrence class | Total | Baseline glossary entry | No baseline entry |", "|---|---:|---:|---:|"]
    for origin in ["first_party_application_base", "first_party_system_or_operations", "derived_view", "extension_managed"]:
        total = origin_gaps[origin] + origin_described[origin]
        summary.append(f"| {origin} | {total} | {origin_described[origin]} | {origin_gaps[origin]} |")
    summary += ["", "A missing baseline entry on a derived-view occurrence points to its lineage, not duplicate business prose. Extension-managed occurrences link to PostGIS documentation. First-party system/operations fields are not automatically end-user requirements.", ""]
    owner_counts = Counter(x["database_owner"] for x in objects)
    summary += ["", "Read-only PostgreSQL relation owners: " + "; ".join(f"`{owner}`: {count} objects" for owner, count in sorted(owner_counts.items())) + ". These are database object owners, not business/product sign-off owners.", "",
                "## Column occurrence categories", "",
                "Counts below describe occurrences in base tables and views. The same logical source attribute may appear more than once in derived views; those rows are not independent business parameters.", "",
                "See `column_occurrence_matrix.csv` for all typed occurrences, `view_column_lineage.csv` for each exact view expression/input, `foreign_key_edges.csv` for the live FK graph, and `api_dependency_map.csv` for literal relation references scoped to backend functions. Static absence is inconclusive. Glossary entries are the preserved 1fee6b5 baseline; missing meanings remain explicitly undocumented.", "",
                "## Domain boundaries and relationship map", "",
                "```mermaid", "erDiagram",
                "  IDENTITY ||--o{ TRIPS : owns", "  IDENTITY ||--o{ CONVERSATIONS : owns",
                "  CONVERSATIONS ||--o{ MESSAGES : contains", "  TRIPS ||--o{ ITINERARIES : plans",
                "  ITINERARIES ||--o{ ITINERARY_STOPS : contains", "  TRIPS ||--o{ TRIP_INTERESTS : records",
                "  TRIPS ||--o{ TRIP_CONSTRAINTS : records", "  ORGANIZATIONS ||--o{ MEMBERSHIPS : scopes",
                "  ORGANIZATIONS ||--o{ SERVICES : owns", "  SERVICES ||--o{ OFFERS : offers",
                "  SERVICES ||--o{ SCHEDULES : schedules", "  SERVICES ||--o{ PRICES : prices",
                "  SERVICES }o--o{ DESTINATIONS : associates", "  KNOWLEDGE_SOURCES ||--o{ DESTINATION_SOURCES : supports",
                "  DESTINATIONS ||--o{ DESTINATION_SOURCES : cited_by", "  DESTINATIONS ||--o{ DESTINATION_CLAIM_EVIDENCE : supports",
                "  TRIPS ||--o{ TRAVELER_REQUEST_SHARES : shared_by_consent", "  TRAVELER_REQUEST_SHARES ||--o{ TRAVELER_REQUEST_REVISIONS : revises",
                "  ORGANIZATIONS ||--o{ TRAVELER_REQUEST_INBOX : receives_authorized", "```", "",
                "The Mermaid view summarizes domain boundaries, not a substitute for the exact live FK graph. `object_decision_matrix.csv` carries the catalog FK edges. Destination identity, source/evidence, and publication are separate: canonical destinations are not source records; claims remain evidence-linked; public catalogue access uses publication views. Conversation messages are not the canonical trip requirements; trip revisions and saved itinerary state remain distinct. Partner memberships and tenant-scoped rows are separate from platform reviewer grants. Traveler sharing requires explicit consent and scoped recipient eligibility; response revisions keep the same request identity.", "",
                "## Risk and impact", "",
                "| Change class | Risk | Required control |", "|---|---|---|",
                "| Drop/rename base relation or column | Critical data loss/API break | Prohibited here; prove consumer graph, migration/backup/restore and explicit owner approval first |",
                "| Change view projection or publication predicate | High public-data/privacy impact | Preserve exact source/eligibility predicate; API contract and negative publication tests |",
                "| Change partner FK/RLS/grants | Critical tenant-isolation risk | Isolated PG17, cross-tenant negative tests, reviewed additive migration |",
                "| Change conversation/trip linkage | High persistence/privacy risk | Existing trip save/reopen and ownership tests |",
                "| Extension catalog changes | Platform compatibility risk | PostgreSQL/PostGIS documented upgrade path; never treat as Rahgard business fields |",
                "| Document-only correction | Low runtime risk | Drift validator and no live write |", "",
                "## Coverage limitation", "",
                "The prior 876 figure was missing glossary coverage among 1,106 column occurrences in this one database snapshot (1,106 minus 230 baseline glossary entries). It is not 876 validated requirements. Derived views repeat source attributes; extension and system metadata are not end-user fields. The matrices classify origins and evidence, but architecture necessity remains `INVESTIGATE` where no sufficient consumer/provenance evidence exists. No schema is declared rational or approved by this audit.", ""]
    (OUTPUT / "ARCHITECTURE_AND_USAGE_REVIEW.md").write_text("\n".join(summary), encoding="utf-8")
    print(json.dumps({"objects": len(objects), "column_occurrences": len(columns), "view_lineage_rows": len(lineage_rows),
                      "decisions": decisions, "output": str(OUTPUT)}, default=dict, sort_keys=True))


if __name__ == "__main__":
    main()
