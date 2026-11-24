"""Zero-network unit tests for the schema dictionary exporter."""
import importlib.util
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).with_name('rahgard_schema_documenter.py')
spec = importlib.util.spec_from_file_location('rahgard_schema_documenter', MODULE)
doc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doc)


class DocumenterTests(unittest.TestCase):
    def test_checked_in_live_schema_package_has_no_drift(self):
        validator_path = Path(__file__).with_name('validate_live_schema_docs.py')
        validator_spec = importlib.util.spec_from_file_location('validate_live_schema_docs', validator_path)
        validator = importlib.util.module_from_spec(validator_spec)
        validator_spec.loader.exec_module(validator)
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(validator.main(), 0)
        self.assertIn('"result": "PASS"', stdout.getvalue())

    def test_safe_slug_no_path_traversal(self):
        self.assertNotIn('/', doc.safe_part('../../secrets'))
        self.assertNotIn('..', doc.safe_part('../../secrets'))

    def test_safe_slug_collision_guard(self):
        self.assertNotEqual(doc.safe_part('a/b'), doc.safe_part('a b'))

    def test_storage_type_does_not_invent_business_contract(self):
        self.assertIn('storage type `jsonb`', doc.type_hint('jsonb'))
        self.assertIn('not inferred', doc.type_hint('numeric(18,2)'))

    def test_timestamp_type_is_not_a_business_timezone_contract(self):
        self.assertIn('timestamp with time zone', doc.type_hint('timestamp with time zone'))
        self.assertIn('not inferred', doc.type_hint('timestamp with time zone'))

    def test_escape_markdown_pipe(self):
        self.assertEqual(doc.escape_cell('a|b'), r'a\|b')

    def test_sensitive_default_hidden(self):
        self.assertIn('پنهان', doc.safe_default("'SECRET-KEY'::text"))
        self.assertIn('پنهان', doc.safe_default("'abc'"))
        self.assertEqual(doc.safe_default('now()'), 'now()')

    def test_per_field_document_and_unknown_gap_count(self):
        relation = {'schema': 'partner', 'name': 'organizations', 'kind': 'r',
                    'rls': True, 'force_rls': False, 'comment': None}
        cols = [
            {'name': 'organization_id', 'pg_type': 'uuid', 'notnull': True,
             'default': 'gen_random_uuid()', 'comment': None, 'identity': '', 'generated': ''},
            {'name': 'display_name', 'pg_type': 'text', 'notnull': False,
             'default': None, 'comment': None, 'identity': '', 'generated': ''},
        ]
        output, gaps = doc.markdown_for_relation('rahgard', relation, cols, [], [], [],
                                                {'partner.organizations': {'display_name': 'نام نمایشی'}},
                                                '2026-11-24T00:00:00Z')
        self.assertIn('نام نمایشی', output)
        self.assertIn('organi', output)
        self.assertIn('RLS', output)
        self.assertEqual(gaps, 1)

    def test_database_specific_overrides(self):
        relation = {'schema': 'private', 'name': 'events', 'kind': 'r', 'rls': False,
                    'force_rls': False, 'comment': None}
        col = [{'name':'id','pg_type':'uuid','notnull':True,'default':None,'comment':None,'identity':'','generated':''}]
        output, gaps = doc.markdown_for_relation('alpha',relation,col,[],[],[],
            {'alpha.private.events': {'id':'کلید رویداد'}},'now')
        self.assertIn('کلید رویداد',output)
        self.assertEqual(gaps,0)

    def test_postgis_views_are_extension_metadata_not_business_fields(self):
        relation = {'schema': 'public', 'name': 'geometry_columns', 'kind': 'v',
                    'rls': False, 'force_rls': False, 'comment': None}
        columns = [{'name': 'f_table_schema', 'pg_type': 'name', 'notnull': False,
                    'default': None, 'comment': None, 'identity': '', 'generated': ''}]
        metadata = {'origin_class': 'extension_managed', 'database_owner': 'postgres',
                    'decision': 'EXTENSION-MANAGED', 'decision_rationale': 'PostGIS catalog',
                    'columns': {'f_table_schema': {'source_evidence': 'https://postgis.net/docs/using_postgis_dbmanagement.html'}}}
        output, gaps = doc.markdown_for_relation('rahgard', relation, columns, [], [], [], {},
                                                 '2026-11-24T00:00:00Z', architecture_metadata=metadata)
        self.assertEqual(gaps, 0)
        self.assertIn('official PostGIS database management documentation', output)
        self.assertNotIn('**UNDOCUMENTED:**', output)
        self.assertIn('EXTENSION-MANAGED', output)

    def test_snapshot_cli_uses_field_descriptions_without_dsn(self):
        snapshot = {
            'created_utc': '2026-11-24T10:00:00Z',
            'scope': 'selected-databases-only',
            'source_release': 'test-release',
            'database_identity': {'database': 'fixture_db', 'server_version': '17'},
            'database_role': 'read_only_fixture',
            'databases_attempted': ['fixture_db'],
            'databases_inaccessible': [],
            'relations': [{
                'database': 'fixture_db',
                'relation': {'schema': 'public', 'name': 'safe_table', 'kind': 'r',
                             'rls': True, 'force_rls': False, 'comment': None},
                'columns': [{'name': 'safe_name', 'pg_type': 'text', 'notnull': True,
                             'default': None, 'comment': None, 'identity': '', 'generated': ''}],
                'constraints': [], 'indexes': [], 'policies': [], 'triggers': [],
            }],
        }
        descriptions = {'fixture_db.public.safe_table': {'safe_name': 'A reviewed display label'}}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot_path = root / 'snapshot.json'
            descriptions_path = root / 'descriptions.json'
            output_path = root / 'output'
            snapshot_path.write_text(json.dumps(snapshot), encoding='utf-8')
            descriptions_path.write_text(json.dumps(descriptions), encoding='utf-8')
            old_env = dict(os.environ)
            try:
                os.environ.pop('RAHGARD_SCHEMA_DSN', None)
                argv = ['rahgard_schema_documenter.py', '--catalog-snapshot-json', str(snapshot_path),
                        '--descriptions-json', str(descriptions_path), '--output-root', str(output_path)]
                with patch('sys.argv', argv), contextlib.redirect_stdout(io.StringIO()) as stdout:
                    self.assertEqual(doc.main(), 0)
                result = json.loads(stdout.getvalue())
                self.assertEqual(result['relations_documented'], 1)
                manifest = json.loads((output_path / 'manifest.json').read_text(encoding='utf-8'))
                self.assertFalse(manifest['complete'])
                self.assertEqual(manifest['coverage_scope'], 'selected-databases-only')
                self.assertNotIn('\\', manifest['relations'][0]['path'])
                relation_doc = next(output_path.rglob('safe_table-*.md')).read_text(encoding='utf-8')
                self.assertIn('A reviewed display label', relation_doc)
                self.assertIn('**0** of **1**', relation_doc)
            finally:
                os.environ.clear()
                os.environ.update(old_env)


if __name__ == '__main__':
    unittest.main()
