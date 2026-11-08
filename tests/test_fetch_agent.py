import importlib.util
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from crossexam.benchmark import source, corpus
from crossexam.scenarios import digest, strengthened
from crossexam.storage import StorageError


@unittest.skipUnless(importlib.util.find_spec('uagents'), 'Optional Fetch uAgents dependency is not installed')
class FetchAgentTests(unittest.TestCase):
    def setUp(self):
        from crossexam.agent import VerifyRequest, VerifyResponse, Identity, evaluate_request, validate_response
        self.Request, self.Response, self.Identity = VerifyRequest, VerifyResponse, Identity
        self.evaluate, self.validate = evaluate_request, validate_response
        suite = strengthened()
        self.report = {'active_version': 1, 'event_root_sha256': 'b'*64,
                       'versions': [{'version': 1, 'accepted': True, 'suite': suite, 'suite_sha256': digest(suite)}]}
        self.archive = SimpleNamespace(read_report=lambda campaign: self.report)

    def test_retrieved_frozen_suite_accepts_correct_and_blocks_broken_code(self):
        for expected, files in [('PASS', source()), ('BLOCKED', next(v.files for v in corpus() if v.id == 'D01'))]:
            request = self.Request(request_id='test', campaign_id='a'*64, files=files)
            result = self.evaluate(request, 'client', self.archive)
            self.assertEqual(result['verdict'], expected)
            self.assertEqual(result['candidate_sha256'], digest(files))
            self.assertEqual(result['suite_sha256'], digest(strengthened()))

    def test_modified_suite_is_rejected_before_execution(self):
        self.report['versions'][0]['suite_sha256'] = '0'*64
        request = self.Request(request_id='test', campaign_id='a'*64, files=source())
        with patch('crossexam.agent.check') as execute, self.assertRaises(StorageError):
            self.evaluate(request, 'client', self.archive)
        execute.assert_not_called()

    def test_extra_candidate_files_are_rejected_before_execution(self):
        request = self.Request(request_id='test', campaign_id='a'*64, files={**source(), 'oracle.py': 'malicious'})
        with patch('crossexam.agent.check') as execute, self.assertRaises(ValueError):
            self.evaluate(request, 'client', self.archive)
        execute.assert_not_called()

    def test_signature_and_request_binding_are_verified(self):
        identity = self.Identity.generate()
        request = self.Request(request_id='test', campaign_id='a'*64, files=source())
        receipt = {'request_id': 'test', 'requester': 'client', 'campaign_id': 'a'*64,
                   'candidate_sha256': digest(source()), 'verdict': 'PASS'}
        signed = self.Response(receipt_json=json.dumps(receipt), signer=identity.address,
                               signature=identity.sign_digest(bytes.fromhex(digest(receipt))))
        self.assertTrue(self.validate(signed, request, identity.address, 'client')['signature_verified'])
        request.request_id = 'another-request'
        with self.assertRaisesRegex(RuntimeError, 'does not match'):
            self.validate(signed, request, identity.address, 'client')
        receipt['verdict'] = 'BLOCKED'
        signed.receipt_json = json.dumps(receipt)
        with self.assertRaisesRegex(RuntimeError, 'signature is invalid'):
            self.validate(signed, request, identity.address, 'client')

    def test_unexpected_signer_is_rejected(self):
        request = self.Request(request_id='test', campaign_id='a'*64, files=source())
        signed = self.Response(receipt_json='{}', signer='someone-else', signature='invalid')
        with self.assertRaisesRegex(RuntimeError, 'unexpected signer'):
            self.validate(signed, request, 'trusted-agent', 'client')


if __name__ == '__main__':
    unittest.main()
