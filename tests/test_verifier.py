import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from crossexam.benchmark import corpus, source
from crossexam.doctor import inspect_sandbox
from crossexam.engine import Campaign, promotion_decision
from crossexam.oracle import evaluate
from crossexam.providers import Partners, ProviderError
from crossexam.runner import check, execute, minimize
from crossexam.scenarios import baseline, strengthened, reserve, release, stock, case, digest, validate_suite


class ContractTests(unittest.TestCase):
    def test_independent_tenants_and_idempotent_retry(self):
        actions = [reserve(qty=8), reserve(qty=8), reserve('beacon', qty=8), stock(), stock('beacon')]
        outputs = evaluate(actions)
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[-2:], [{'available': 2}, {'available': 2}])

    def test_release_does_not_mint_stock(self):
        result = evaluate([reserve(), release(), release(), stock(), reserve(), stock()])
        self.assertEqual(result[3], {'available': 10})
        self.assertEqual(result[-1], {'available': 10})

    def test_failed_key_can_be_retried(self):
        result = evaluate([reserve(qty=8), reserve(key='retry', qty=4), release(), reserve(key='retry', qty=4), stock()])
        self.assertEqual(result[1], {'error': 'insufficient'})
        self.assertEqual(result[-1], {'available': 6})

    def test_bool_float_and_negative_are_rejected(self):
        for qty in (True, False, 2.0, -1, 0, 11, '2'):
            self.assertEqual(evaluate([reserve(qty=qty)])[0], {'error':'invalid'})

    def test_bad_suite_rejected_before_execution(self):
        for suite in ([], [{'name':'bad','family':'unknown','actions':[{}]}], [{'name':'bad','family':'inventory','actions':[]} ]):
            with self.assertRaises(ValueError): validate_suite(suite)


class GateTests(unittest.TestCase):
    def score(self, caught, false=0):
        return {'false_rejections': false, 'rows': [{'id':i,'detected':True,'correct':False} for i in caught]}

    def test_gain_with_regression_rejected(self):
        self.assertFalse(promotion_decision(self.score(['a','b']), self.score(['b','c','d']))[0])

    def test_gain_with_false_rejection_rejected(self):
        self.assertFalse(promotion_decision(self.score(['a']), self.score(['a','b'],1))[0])

    def test_no_gain_rejected(self):
        self.assertFalse(promotion_decision(self.score(['a']), self.score(['a']))[0])

    def test_strict_gain_accepted(self):
        self.assertTrue(promotion_decision(self.score(['a']), self.score(['a','b']))[0])

    def test_test_author_does_not_receive_implementation(self):
        with tempfile.TemporaryDirectory() as tmp:
            partner=Partners(tmp)
            with patch.object(partner,'meta_json',return_value={'cases':[case('test','inventory',stock())]}) as mock:
                partner.propose(baseline(),[],['inventory'],1)
            context=mock.call_args.args[2]
            self.assertEqual(set(context),{'contract','current_suite','observed_counterexamples','focus_families'})
            self.assertNotIn('class Service',json.dumps(context))
            self.assertNotIn('oracle',json.dumps(context))

    def test_live_mode_never_silently_substitutes_fixtures(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ',{'SUBQ_API_KEY':''}):
            with self.assertRaises(ProviderError): Partners(tmp).route(baseline())


class ExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inspection=inspect_sandbox()

    def test_sandbox_enforcement(self):
        self.assertTrue(all(self.inspection['checks'].values()))

    def test_all_correct_controls_agree_with_contract(self):
        for v in corpus():
            if v.correct:
                with self.subTest(variant=v.id):
                    result=check(v.files,strengthened())
                    self.assertIsNone(result['error'])
                    self.assertTrue(result['passed'])

    def test_green_suite_hides_real_tenant_leak(self):
        v=next(v for v in corpus() if v.id=='D01')
        self.assertTrue(check(v.files,baseline())['passed'])
        result=check(v.files,strengthened())
        self.assertFalse(result['passed'])
        witness=minimize(v.files,result['failure'])
        self.assertEqual(len(witness['actions']),2)
        self.assertEqual(witness['actual'][-1]['tenant'],'atlas')
        self.assertEqual(witness['expected'][-1]['tenant'],'beacon')

    def test_missing_or_extra_candidate_files_rejected(self):
        with self.assertRaises(ValueError): execute({'service.py':'','cache.py':'','oracle.py':''},baseline())

    def test_output_flood_is_bounded(self):
        result=execute({'service.py':'class Service:\n def handle(self, a):\n  print("x" * 1100000)\n  return {}\n','cache.py':''},baseline())
        self.assertIsNotNone(result['error'])
        self.assertLess(result['seconds'],10)

    def test_full_campaign_orders_audit_after_learning(self):
        with tempfile.TemporaryDirectory() as tmp:
            campaign=Campaign(Path(tmp)/'run')
            report=campaign.run()
            audit_index=next(i for i,e in enumerate(report['events']) if e['kind']=='audit_opened')
            self.assertFalse(any(e['kind'] in ('proposal','promotion','suite_frozen') for e in report['events'][audit_index+1:]))
            self.assertEqual(report['audit_after']['false_rejections'],0)
            self.assertGreater(report['audit_after']['detected'],report['audit_before']['detected'])
            self.assertFalse(report['versions'][-1]['accepted'])
            previous='0'*64
            for event in report['events']:
                self.assertEqual(event['previous'],previous)
                self.assertEqual(event['sha256'],digest({k:v for k,v in event.items() if k!='sha256'}))
                previous=event['sha256']


if __name__=='__main__': unittest.main()
