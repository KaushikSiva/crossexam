"""Corpus qualification; these witnesses never enter live model contexts."""

from concurrent.futures import ThreadPoolExecutor
import unittest

from crossexam.benchmark import corpus
from crossexam.runner import check
from crossexam.scenarios import reserve as r, release as l, stock as s, case, digest, strengthened


def missing(action, field):
    return {k: v for k, v in action.items() if k != field}


def witnesses():
    return {
        'V09': [r(key='ORDER'), r(key='order'), s()],
        'V10': [r(tenant=' atlas'), r(), s()],
        'V11': [r(key='request-001'), r(key='request-002'), s()],
        'V12': [r(), l(), r()],
        'V13': [r(), r(key='second'), r(), s()],
        'V14': [r(), l(key='missing'), r(), s()],
        'V15': [r(qty=8), r(key='later', qty=4), l(), r(key='later', qty=4), s()],
        'V16': [r(), r()],
        'V17': [r(), r(qty=3), r(), s()],
        'V18': [r(), r(qty=3), s()],
        'V19': [r(), l(), r(qty=3)],
        'V20': [r(), r(sku='sensor'), s()],
        'V21': [r(sku='sensor'), l(), s(sku='sensor'), s()],
        'V22': [r(), r(key='second'), l(), s()],
        'V23': [r(sku='sensor'), s(sku='sensor')],
        'V24': [r(qty=8), r(key='second', qty=4), s()],
        'V25': [r(qty=10)],
        'V26': [r(qty='2'), s()],
        'V27': [missing(r(), 'tenant'), s()],
        'V28': [{**r(), 'op': 'unknown'}, s()],
        'V29': [s(sku='unknown')],
        'V30': [l(key='')],
        'A09': [r(key='order'), r(key=' order '), s()],
        'A10': [r(tenant='customer-east'), r(tenant='customer-west'), s('customer-west')],
        'A11': [r(tenant='ab', key='c'), r(tenant='a', key='bc')],
        'A12': [r(), r(), r(), s()],
        'A13': [r(), r(qty=0), r(), s()],
        'A14': [r(), r(key='second'), l(), l(key='second'), s()],
        'A15': [r(), r()],
        'A16': [r(), r(qty=3)],
        'A17': [r(), r(qty=3), l(), s()],
        'A18': [r(), r(sku='sensor'), l(), s(), s(sku='sensor')],
        'A19': [r(), l(), r(qty=3)],
        'A20': [r(), l(), s()],
        'A21': [r(), s()],
        'A22': [r(qty=10), s()],
        'A23': [s()],
        'A24': [r(sku='sensor'), s()],
        'A25': [r(qty=1)],
        'A26': [{**r(), 'trace_id': 'ignored-by-contract'}],
        'A27': [r(key=7)],
        'A28': [missing(r(), 'qty')],
        'A29': [s()],
        'A30': [r(), l()],
    }


class ExpandedBenchmarkTests(unittest.TestCase):
    def test_sixty_distinct_faulty_sources_and_stable_ids(self):
        variants = corpus()
        for split, prefix in [('validation', 'V'), ('audit', 'A')]:
            rows = [v for v in variants if v.split == split]
            self.assertEqual({v.id for v in rows}, {f'{prefix}{n:02d}' for n in range(1, 31)})
            self.assertFalse(any(v.correct for v in rows))
        self.assertEqual(len({digest(v.files) for v in variants}), len(variants))
        for v in variants:
            for name, code in v.files.items():
                compile(code, name, 'exec')

    def test_every_added_fault_has_an_executable_contract_witness(self):
        by_id = {v.id: v for v in corpus()}
        def reproduce(item):
            identifier, actions = item
            return identifier, check(by_id[identifier].files, [case(identifier, 'mixed', *actions)])
        with ThreadPoolExecutor(max_workers=4) as pool:
            for identifier, result in pool.map(reproduce, witnesses().items()):
                with self.subTest(variant=identifier):
                    self.assertIsNone(result['error'])
                    self.assertFalse(result['passed'])
                    self.assertIsNotNone(result['failure'])

    def test_all_correct_controls_pass_all_qualification_witnesses(self):
        suite = [case(k, 'mixed', *actions) for k, actions in witnesses().items()]
        for v in corpus():
            if v.correct:
                with self.subTest(variant=v.id):
                    result = check(v.files, suite)
                    self.assertIsNone(result['error'])
                    self.assertTrue(result['passed'])

    def test_original_faults_remain_executable_contract_violations(self):
        suite = strengthened() + [case('depleted replay', 'idempotency', r(qty=8), r(qty=8), s())]
        for v in corpus():
            if not v.correct and (v.id.startswith('D') or int(v.id[1:]) <= 8):
                with self.subTest(variant=v.id):
                    result = check(v.files, suite)
                    self.assertIsNone(result['error'])
                    self.assertFalse(result['passed'])


if __name__ == '__main__':
    unittest.main()
