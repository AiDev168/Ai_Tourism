from __future__ import annotations
import hashlib, os, re, subprocess

CONTAINER=os.environ.get('RAHGARD_DEMO_DB_CONTAINER','')
MARKER=os.environ.get('RAHGARD_PILOT_DATABASE_MARKER','')
ROOT=__import__('pathlib').Path(__file__).resolve().parents[3]
DB='rahgard_pilot_vps_staging'
if not re.fullmatch(r'rahgard-issue27-[0-9a-f]{12}-db-1', CONTAINER) or not re.fullmatch(r'[a-f0-9]{48}', MARKER):
    raise SystemExit('BLOCKED: local database identity is invalid')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def docker(args, data=None, env=None):
    res=subprocess.run(['docker',*args],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,**(env or {})})
    if res.returncode:
        text=res.stderr.decode('utf8','replace')
        state=re.search(r'ERROR:\s+([0-9A-Z]{5}):',text)
        msg=re.search(r'ERROR:\s*(?:[0-9A-Z]{5}:\s*)?(permission denied for (?:schema|table|relation|function) [A-Za-z0-9_.]+|must be owner of (?:table|function|schema) [A-Za-z0-9_.]+)',text,re.I)
        suffix=(f' sqlstate={state.group(1)}' if state else '')+(f' reason={msg.group(1)}' if msg else '')
        raise SystemExit('BLOCKED: local migration command failed'+suffix)
    return res.stdout
def scalar(sql):
    return docker(['exec',CONTAINER,'psql','-X','-q','-A','-t','-U','ai_tourism_owner','-d',DB,'-c',sql]).decode().strip()
def psql(sql, *, as_role=None, env=None):
    prefix=(f'SET ROLE {as_role};\n' if as_role else '')
    script=b'\\getenv marker RAHGARD_PILOT_DATABASE_MARKER\n'+(prefix+sql).encode()
    command=['exec','-i','-e',f'RAHGARD_PILOT_DATABASE_MARKER={MARKER}']
    for key,value in (env or {}).items(): command.extend(['-e',f'{key}={value}'])
    command += [CONTAINER,'sh','-lc','export PGPASSWORD="$(cat /run/secrets/pg_owner_password)"; exec psql -X -v ON_ERROR_STOP=1 -v VERBOSITY=verbose -h 127.0.0.1 -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
    docker(command,data=script)

if scalar('SELECT current_database()') != DB or scalar("SELECT current_setting('server_version_num')::int BETWEEN 170000 AND 179999") != 't':
    raise SystemExit('BLOCKED: local database identity or PG major differs')
if scalar('SELECT count(*) FROM public.rahgard_private_pilot_marker') != '1' or scalar('SELECT min(marker_value) FROM public.rahgard_private_pilot_marker') != MARKER:
    raise SystemExit('BLOCKED: local database marker mismatch')
ledger=scalar("SELECT count(*)||':'||max(migration_id) FROM system.schema_migrations")
if ledger in {'26:0027_server_ai_provider_admin','28:0027_server_ai_provider_admin'}:
    print('ALREADY_APPLIED: 0027 checksum='+sha(ROOT/'engineering/pilot/sql/027_server_ai_provider_admin.sql')+'; NO DDL')
    raise SystemExit(0)
if ledger not in {'25:0026_platform_reviewer_mfa','27:0026_platform_reviewer_mfa'} or scalar("SELECT to_regnamespace('ai_provider') IS NULL") != 't':
    raise SystemExit('BLOCKED: exact baseline ledger/schema not found; preserve the volume')
for mid,file in [('0024_partner_review_audit_actions','024_partner_review_audit_actions.sql'),('0025_owner_control_center','025_owner_control_center.sql'),('0026_platform_reviewer_mfa','026_platform_reviewer_mfa.sql')]:
    expected=sha(ROOT/'engineering/pilot/sql'/file)
    if scalar(f"SELECT sha256 FROM system.schema_migrations WHERE migration_id='{mid}'") != expected:
        raise SystemExit('BLOCKED: migration checksum differs')
pre=scalar("SELECT (SELECT count(*) FROM identity.users)||':'||(SELECT count(*) FROM travel.trips)||':'||(SELECT count(*) FROM conversation.conversations)||':'||(SELECT count(*) FROM partner.organizations)")
path=ROOT/'engineering/pilot/sql/027_server_ai_provider_admin.sql'
h=sha(path)
env={'RAHGARD_PILOT_MIGRATION_0024_SHA256':sha(ROOT/'engineering/pilot/sql/024_partner_review_audit_actions.sql'),'RAHGARD_PILOT_MIGRATION_0025_SHA256':sha(ROOT/'engineering/pilot/sql/025_owner_control_center.sql'),'RAHGARD_PILOT_MIGRATION_0026_SHA256':sha(ROOT/'engineering/pilot/sql/026_platform_reviewer_mfa.sql'),'RAHGARD_PILOT_MIGRATION_0027_SHA256':h}
psql('''GRANT USAGE ON SCHEMA system,partner,public TO rahgard_pilot_ddl_owner;
GRANT SELECT,INSERT ON system.schema_migrations TO rahgard_pilot_ddl_owner;
GRANT SELECT ON public.rahgard_private_pilot_marker TO rahgard_pilot_ddl_owner;
GRANT SELECT(user_id,enabled_at) ON identity.platform_admin_mfa TO rahgard_pilot_ddl_owner;
GRANT SELECT(user_id,session_id,revoked_at,expires_at) ON identity.platform_admin_step_up TO rahgard_pilot_ddl_owner;
GRANT EXECUTE ON FUNCTION identity.has_platform_admin_capability(UUID),partner.current_actor_id() TO rahgard_pilot_ddl_owner;''',env=env)
try:
    psql('\\set migration_hash '+h+'\n'+path.read_text(encoding='utf8'),as_role='rahgard_pilot_ddl_owner',env=env)
finally:
    psql('''REVOKE SELECT,INSERT ON system.schema_migrations FROM rahgard_pilot_ddl_owner;
REVOKE USAGE ON SCHEMA system,public FROM rahgard_pilot_ddl_owner;
REVOKE SELECT ON public.rahgard_private_pilot_marker FROM rahgard_pilot_ddl_owner;''')
if scalar("SELECT sha256 FROM system.schema_migrations WHERE migration_id='0027_server_ai_provider_admin'") != h:
    raise SystemExit('BLOCKED: 0027 checksum not recorded')
post=scalar("SELECT (SELECT count(*) FROM identity.users)||':'||(SELECT count(*) FROM travel.trips)||':'||(SELECT count(*) FROM conversation.conversations)||':'||(SELECT count(*) FROM partner.organizations)")
if post != pre:
    raise SystemExit('BLOCKED: application row counts changed; preserve volume for inspection')
print('PASS: local-only additive migration 0027; checksum='+h+'; ledger='+scalar("SELECT count(*)||':'||max(migration_id) FROM system.schema_migrations")+'; aggregate_counts_preserved='+pre)
