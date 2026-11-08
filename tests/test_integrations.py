import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

from crossexam.benchmark import corpus
from crossexam.engine import Campaign
from crossexam.providers import Partners, ProviderError, json_object, load_env, readiness
from crossexam.scenarios import baseline, reserve, strengthened
from crossexam.storage import MongoArchive, StorageError


def response(value, provider):
    text = json.dumps(value)
    if provider == 'gemini':
        return {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': text}]}}],
                'usageMetadata': {'promptTokenCount': 20, 'candidatesTokenCount': 10, 'thoughtsTokenCount': 4}}
    return {'choices': [{'finish_reason': 'stop', 'message': {'content': text}}],
            'usage': {'prompt_tokens': 20, 'completion_tokens': 10}}


class ProviderTests(unittest.TestCase):
    def test_env_aliases_and_existing_values(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'GEMINI_MODEL': 'existing'}, clear=True):
            path = Path(tmp) / '.env'
            path.write_text('GOOGLE_API_KEY=google\nFETCHAI_KEY=fetch\nGEMINI_MODEL=other\nMONGODB_URI=mongodb://localhost\nUNRELATED_SECRET=ignored\n')
            load_env(path)
            self.assertTrue(all(readiness()[p] for p in ('gemini', 'fetchai', 'mongodb')))
            self.assertEqual(os.environ['GEMINI_MODEL'], 'existing')
            self.assertNotIn('UNRELATED_SECRET', os.environ)

    def test_transport_auth_schema_usage_and_secret_free_evidence(self):
        for provider, key in [('gemini', 'GEMINI_API_KEY'), ('fetchai', 'ASI_ONE_API_KEY')]:
            with self.subTest(provider=provider), tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {key: 'secret-test-key'}, clear=True):
                http = MagicMock()
                http.__enter__.return_value.read.return_value = json.dumps(response({'ready': True}, provider)).encode()
                with patch('urllib.request.urlopen', return_value=http) as request:
                    p = Partners(tmp, generator=provider, max_calls=1)
                    self.assertEqual(p.generate_json('probe', 'Return JSON', {}, json_object({'ready': {'type': 'boolean'}})), {'ready': True})
                req = request.call_args.args[0]
                payload = json.loads(req.data)
                if provider == 'gemini':
                    self.assertEqual(req.full_url, 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent')
                    self.assertEqual(req.get_header('X-goog-api-key'), 'secret-test-key')
                    self.assertNotIn('model', payload)
                    self.assertEqual(payload['generationConfig']['responseFormat']['text']['mimeType'], 'APPLICATION_JSON')
                    self.assertEqual(p.calls[0]['usage']['input_tokens'], 20)
                else:
                    self.assertEqual(req.full_url, 'https://api.asi1.ai/v1/chat/completions')
                    self.assertEqual(req.get_header('Authorization'), 'Bearer secret-test-key')
                    self.assertTrue(payload['response_format']['json_schema']['strict'])
                    self.assertNotIn('planner_mode', payload)
                for artifact in Path(tmp).glob('*.json'):
                    self.assertNotIn('secret-test-key', artifact.read_text())
                with self.assertRaises(ProviderError):
                    p.generate_json('over-budget', '', {}, json_object({}))

    def test_missing_keys_do_not_make_network_requests(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True), patch('urllib.request.urlopen') as http:
            for provider in ('gemini', 'fetchai'):
                with self.assertRaises(ProviderError):
                    Partners(tmp, generator=provider).generate_json('test', '', {}, json_object({}))
            http.assert_not_called()

    def test_refusals_truncation_non_objects_and_bad_json_fail_closed(self):
        bad = {
            'gemini': [{}, {'candidates': []}, {'candidates': [None]}, response([], 'gemini'),
                       {'candidates': [{'finishReason': 'MAX_TOKENS', 'content': {'parts': [{'text': '{}'}]}}]},
                       {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': 'bad'}]}}]},
                       {**response({}, 'gemini'), 'promptFeedback': {'blockReason': 'SAFETY'}}],
            'fetchai': [{}, {'choices': []}, {'choices': [None]}, response([], 'fetchai'),
                        {'choices': [{'finish_reason': 'length', 'message': {'content': '{}'}}]},
                        {'choices': [{'finish_reason': 'stop', 'message': {'content': '{}', 'refusal': 'No'}}]},
                        {'choices': [{'finish_reason': 'stop', 'message': {'content': 'bad'}}]}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            for provider, values in bad.items():
                p = Partners(tmp, generator=provider)
                for value in values:
                    with self.subTest(provider=provider, value=value), patch.object(p, 'request', return_value=value):
                        with self.assertRaises(ProviderError):
                            p.generate_json('test', '', {}, json_object({}))

    def test_test_author_preserves_input_types_and_has_no_implementation(self):
        value = {'cases': [{'name': 'boolean quantity', 'family': 'validation', 'actions_json': json.dumps([reserve(qty=True)])}], 'rationale': 'Invalid input boundary'}
        with tempfile.TemporaryDirectory() as tmp:
            for author in ('gemini', 'fetchai'):
                p = Partners(tmp, generator='openai', test_author=author)
                with patch.object(p, 'request', return_value=response(value, author)) as req:
                    cases, _ = p.propose(baseline(), [], ['validation'], 1, feedback=[])
                self.assertIs(cases[0]['actions'][0]['qty'], True)
                self.assertEqual(req.call_args.args[0], author)
                payload = req.call_args.args[2]
                context = json.loads(payload['contents'][0]['parts'][0]['text'] if author == 'gemini' else payload['messages'][1]['content'])
                self.assertEqual(set(context), {'contract', 'current_suite', 'observed_counterexamples', 'focus_families', 'previous_validation_feedback'})
                self.assertNotIn('class Service', json.dumps(context))

    def test_malformed_http_response_is_recorded_as_failed(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}):
            http = MagicMock()
            http.__enter__.return_value.read.return_value = b'[]'
            p = Partners(tmp, generator='gemini')
            with patch('urllib.request.urlopen', return_value=http), self.assertRaises(ProviderError):
                p.generate_json('test', '', {}, json_object({}))
            self.assertEqual(p.calls[0]['status'], 'failed')

    def test_malformed_actions_get_one_audited_repair_within_shared_budget(self):
        invalid = {'cases': [{'name': 'bad', 'family': 'inventory', 'actions_json': '[{}]}],'}], 'rationale': 'test'}
        valid = {'cases': [{'name': 'stock', 'family': 'inventory', 'actions_json': '[{"op":"stock","tenant":"a","sku":"widget"}]'}], 'rationale': 'test'}
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'ASI_ONE_API_KEY': 'test'}):
            p = Partners(tmp, generator='fetchai', max_calls=2)
            replies = iter([invalid, valid])
            def http(*args, **kwargs):
                mock = MagicMock()
                mock.__enter__.return_value.read.return_value = json.dumps(response(next(replies), 'fetchai')).encode()
                return mock
            with patch('urllib.request.urlopen', side_effect=http):
                cases, _ = p.propose(baseline(), [], ['inventory'], 1)
            self.assertEqual(cases[0]['name'], 'stock')
            self.assertEqual([c['status'] for c in p.calls], ['invalid_response', 'complete'])
            self.assertEqual(p.calls[1]['purpose'], 'test-proposal-1-repair-1')
            self.assertEqual(len(list(Path(tmp).glob('*response.json'))), 2)
            with self.assertRaisesRegex(ProviderError, 'budget'):
                p.propose(baseline(), [], ['inventory'], 2)

    def test_mixed_campaign_keeps_shared_budget_and_records_both_roles(self):
        attack = {'title': 'Mock attack', 'family': 'tenant_isolation', 'files': next(v.files for v in corpus() if v.id == 'D01')}
        proposal = {'cases': [{**{k:v for k,v in case.items() if k != 'actions'}, 'actions_json': json.dumps(case['actions'])} for case in strengthened()[4:]], 'rationale': 'Mock contract tests'}
        routing = {'order': ['tenant_isolation', 'idempotency', 'payload_binding', 'inventory', 'validation'], 'origin': 'mock', 'scores': {}}
        with tempfile.TemporaryDirectory() as tmp, patch.object(Partners, 'route', return_value=routing), patch.dict(os.environ, {'GEMINI_API_KEY': 'test', 'ASI_ONE_API_KEY': 'test'}):
            def http(req, **kwargs):
                result = response(attack, 'gemini') if 'googleapis' in req.full_url else response(proposal, 'fetchai')
                mock = MagicMock()
                mock.__enter__.return_value.read.return_value = json.dumps(result).encode()
                return mock
            with patch('urllib.request.urlopen', side_effect=http):
                campaign = Campaign(Path(tmp)/'run', live=True, generator='gemini', test_author='fetchai')
                report = campaign.run()
            self.assertEqual([c['provider'] for c in report['provider_calls']], ['gemini'] + ['fetchai']*4)
            self.assertEqual(report['manifest']['proposal_protocol']['test_author'], 'fetchai')
            self.assertTrue(all('Fetch.ai' in v['origin'] for v in report['versions'][1:]))
            self.assertEqual(report['audit_after']['false_rejections'], 0)
            self.assertIn('Google DeepMind', report['manifest']['mode'])


class MongoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        report = {'schema': 2, 'event_root_sha256': 'a'*64, 'manifest': {'mode': 'local fixtures', 'created_at': '2026-11-08'},
                  'audit_after': {'detected': 7, 'total': 8, 'false_rejections': 0}}
        (self.folder/'report.json').write_text(json.dumps(report))
        (self.folder/'suite-v0.json').write_text('{"qty": true, "missing": null, "$key": 2}')
        (self.folder/'.env').write_text('MONGODB_URI=secret')
        self.db = MagicMock()
        self.client = MagicMock()
        self.client.__getitem__.return_value = self.db
        self.error = type('PyMongoError', (Exception,), {})
        self.modules = {'pymongo': types.SimpleNamespace(MongoClient=MagicMock(return_value=self.client)),
                        'pymongo.errors': types.SimpleNamespace(PyMongoError=self.error)}
        self.addCleanup(patch.stopall)
        patch.dict('sys.modules', self.modules).start()
        patch.dict(os.environ, {'MONGODB_URI': 'mongodb://user:secret@localhost', 'MONGODB_DATABASE': 'crossexam-test'}).start()

    def test_archive_is_idempotent_and_excludes_secrets(self):
        with MongoArchive() as archive:
            first = archive.archive(self.folder)
            second = archive.archive(self.folder)
        self.assertEqual(first, second)
        self.assertEqual(first['artifacts'], 2)
        campaign_calls = self.db.campaigns.update_one.call_args_list
        self.assertEqual(campaign_calls[0], campaign_calls[1])
        self.assertTrue(campaign_calls[0].kwargs['upsert'])
        self.assertNotIn('secret', str(self.db.mock_calls))
        self.assertNotIn('secret', (self.folder/'mongodb-receipt.json').read_text())
        self.assertTrue(self.client.close.called)
        for call in self.db.artifacts.update_one.call_args_list:
            self.assertIn('$setOnInsert', call.args[1])

    def test_partial_failure_has_no_completed_record_and_can_retry(self):
        self.db.artifacts.update_one.side_effect = self.error('secret connection details')
        with MongoArchive() as archive:
            with self.assertRaises(StorageError) as caught:
                archive.archive(self.folder)
            self.assertNotIn('secret', str(caught.exception))
            self.db.campaigns.update_one.assert_not_called()
            self.assertFalse((self.folder/'mongodb-receipt.json').exists())
            self.assertTrue((self.folder/'report.json').exists())
            self.db.artifacts.update_one.side_effect = None
            self.assertEqual(archive.archive(self.folder)['status'], 'complete')

    def test_connection_error_is_redacted(self):
        self.client.admin.command.side_effect = self.error('mongodb://user:secret@localhost')
        with self.assertRaises(StorageError) as caught:
            MongoArchive()
        self.assertNotIn('secret', str(caught.exception))
        self.client.close.assert_called_once()

    def test_readback_detects_changed_evidence(self):
        with MongoArchive() as archive:
            archive.archive(self.folder)
            record = self.db.campaigns.update_one.call_args.args[1]['$setOnInsert']
            artifacts = {c.args[0]['_id']: c.args[1]['$setOnInsert'] for c in self.db.artifacts.update_one.call_args_list}
            self.db.campaigns.find_one.return_value = record
            self.db.artifacts.find_one.side_effect = lambda query: artifacts.get(query['_id'])
            self.assertEqual(archive.verify(self.folder)['artifacts_verified'], 2)
            artifacts[next(iter(artifacts))]['content'] = 'changed'
            with self.assertRaisesRegex(StorageError, 'missing or changed'):
                archive.verify(self.folder)

    def test_unacknowledged_writes_are_not_reported_as_success(self):
        self.db.artifacts.update_one.return_value.acknowledged = False
        with MongoArchive() as archive, self.assertRaises(StorageError):
            archive.archive(self.folder)
        self.db.campaigns.update_one.assert_not_called()

    def test_missing_uri_is_explicit(self):
        with patch.dict(os.environ, {'MONGODB_URI': ''}), self.assertRaisesRegex(StorageError, 'MONGODB_URI'):
            MongoArchive()


if __name__ == '__main__':
    unittest.main()
