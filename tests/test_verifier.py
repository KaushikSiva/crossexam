import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from crossexam.benchmark import corpus, source
from crossexam.doctor import inspect_sandbox
from crossexam.engine import Campaign, promotion_decision
from crossexam.oracle import evaluate
from crossexam.providers import Partners, ProviderError, json_object, readiness
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

    def test_openai_parses_response_and_preserves_invalid_input_types(self):
        value={'cases':[{'name':'boolean quantity','family':'validation','actions_json':json.dumps([reserve(qty=True)])}], 'rationale':'Check the contract'}
        response={'status':'completed','output':[{'type':'reasoning'}, {'type':'message','content':[{'type':'output_text','text':json.dumps(value)}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            p=Partners(tmp,generator='openai')
            with patch.object(p,'request',return_value=response) as request:
                cases,_=p.propose(baseline(),[],['validation'],1,feedback=[])
            self.assertIs(cases[0]['actions'][0]['qty'],True)
            payload=request.call_args.args[2]
            self.assertFalse(payload['store'])
            self.assertTrue(payload['text']['format']['strict'])
            context=json.loads(payload['input'][0]['content'])
            self.assertEqual(set(context),{'contract','current_suite','observed_counterexamples','focus_families','previous_validation_feedback'})
            self.assertNotIn('class Service',json.dumps(context))
            self.assertNotIn('previous_response_id',payload)

    def test_openai_refusal_truncation_and_malformed_json_fail_closed(self):
        responses=[{'status':'incomplete','output':[]},
                   {'status':'completed','output':[{'type':'message','content':[{'type':'refusal','refusal':'No'}]}]},
                   {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'broken'}]}]}]
        with tempfile.TemporaryDirectory() as tmp:
            p=Partners(tmp,generator='openai')
            for response in responses:
                with self.subTest(response=response), patch.object(p,'request',return_value=response):
                    with self.assertRaises(ProviderError): p.openai_json('test','test',{},json_object({}))

    def test_openai_does_not_need_meta_key_and_archives_no_authorization(self):
        response={'status':'completed','output':[], 'usage':{}}
        from unittest.mock import MagicMock
        http=MagicMock()
        http.__enter__.return_value.read.return_value=json.dumps(response).encode()
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ',{'OPENAI_API_KEY':'secret-for-test-only','MODEL_API_KEY':''}), patch('urllib.request.urlopen',return_value=http) as request:
            p=Partners(tmp,generator='openai',max_calls=1)
            self.assertTrue(readiness()['openai'])
            self.assertFalse(readiness()['meta'])
            p.request('openai','test',{'model':'test'})
            self.assertEqual(request.call_args.args[0].full_url,'https://api.openai.com/v1/responses')
            for path in Path(tmp).glob('*.json'):
                self.assertNotIn('secret-for-test-only',path.read_text())
            with self.assertRaises(ProviderError): p.request('openai','over-budget',{'model':'test'})


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

    def test_subq_only_calls_router_without_meta_generation(self):
        routing={'order':['tenant_isolation','idempotency','validation','payload_binding','inventory'],
                 'scores':{},'origin':'mocked router for test','note':'No network request in this test.'}
        with tempfile.TemporaryDirectory() as tmp, patch.object(Partners,'route',return_value=routing) as route, patch.object(Partners,'attack') as attack, patch.object(Partners,'propose') as propose:
            report=Campaign(Path(tmp)/'run',subq_only=True).run()
            route.assert_called_once()
            attack.assert_not_called()
            propose.assert_not_called()
            self.assertEqual(report['manifest']['mode'],'live Subquadratic + local proposals')
            self.assertEqual(report['audit_after']['false_rejections'],0)

    def test_live_records_real_plateau_without_injected_rollback(self):
        routing={'order':['tenant_isolation','idempotency','validation','payload_binding','inventory'],'scores':{},'origin':'mock','note':'test'}
        attack={'title':'Seed supplied by mock','family':'tenant_isolation','files':next(v.files for v in corpus() if v.id=='D01')}
        feedback=[]
        def proposal(suite,failures,families,round_number,**kwargs):
            feedback.append(json.loads(json.dumps(kwargs['feedback'])))
            return strengthened()[4:], 'Mock generated inputs'
        with tempfile.TemporaryDirectory() as tmp, patch.object(Partners,'route',return_value=routing), patch.object(Partners,'attack',return_value=attack), patch.object(Partners,'propose',side_effect=proposal) as propose:
            report=Campaign(Path(tmp)/'run',live=True).run()
            self.assertEqual(propose.call_count,4)
            self.assertEqual([v['accepted'] for v in report['versions']],[True,True,False,False,False])
            self.assertTrue(all('system-injected' not in v['origin'] for v in report['versions']))
            self.assertEqual(len(feedback[-1]),3)
            self.assertNotIn('rows',feedback[-1][0])
            self.assertFalse(report['manifest']['proposal_protocol']['injected_rollback'])
            opened=next(e['sequence'] for e in report['events'] if e['kind']=='audit_opened')
            self.assertTrue(all(e['sequence']<opened for e in report['events'] if e['kind']=='proposal'))


if __name__=='__main__': unittest.main()
