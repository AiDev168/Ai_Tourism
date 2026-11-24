"""Zero-network unit tests for the schema dictionary exporter."""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).with_name('rahgard_schema_documenter.py')
spec = importlib.util.spec_from_file_location('rahgard_schema_documenter', MODULE)
doc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doc)


class DocumenterTests(unittest.TestCase):
    def test_safe_slug_no_path_traversal(self):
        self.assertNotIn('/', doc.safe_part('../../secrets'))
        self.assertNotIn('..', doc.safe_part('../../secrets'))

    def test_safe_slug_collision_guard(self):
        self.assertNotEqual(doc.safe_part('a/b'), doc.safe_part('a b'))

    def test_jsonb_format(self):
        self.assertIn('JSON', doc.type_hint('jsonb'))

    def test_numeric_format(self):
        self.assertIn('ده‌دهی', doc.type_hint('numeric(18,2)'))

    def test_timestamp_format(self):
        self.assertIn('ISO 8601', doc.type_hint('timestamp with time zone'))

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


if __name__ == '__main__':
    unittest.main()
