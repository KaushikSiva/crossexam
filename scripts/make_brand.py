"""Create original vector artwork and narration from a measured run."""

import argparse
import html
import json
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument("report",type=Path)
args=parser.parse_args()
r=json.loads(args.report.read_text())
out=Path("docs/assets");out.mkdir(parents=True,exist_ok=True)
b,a=r["audit_before"],r["audit_after"]
banner=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="800" viewBox="0 0 1600 800">
<rect width="1600" height="800" fill="#111111"/>
<g stroke="#353535" stroke-width="1"><path d="M0 670H1600M1040 0V800"/><path d="M1100 120L1480 500M1480 120L1100 500" stroke-width="95"/></g>
<path d="M70 67l28 28m0-28L70 95" stroke="#f5f5f5" stroke-width="8"/>
<text x="120" y="89" fill="#a6a6a6" font-family="monospace" font-size="17" letter-spacing="3">ADVERSARIAL EVALS FOR CODING AGENTS</text>
<text x="65" y="257" fill="#f7f7f7" font-family="Arial, sans-serif" font-size="128" font-weight="bold" letter-spacing="-8">CrossExam</text>
<text x="74" y="356" fill="#f7f7f7" font-family="Arial, sans-serif" font-size="51" letter-spacing="-2">Your tests passed.</text>
<text x="74" y="425" fill="#f5f5f5" font-family="Arial, sans-serif" font-size="51" letter-spacing="-2">Your software failed.</text>
<text x="75" y="502" fill="#acacac" font-family="Arial, sans-serif" font-size="23">Find the counterexample. Improve the evaluation.</text>
<text x="75" y="538" fill="#acacac" font-family="Arial, sans-serif" font-size="23">Prove the improvement on different implementations.</text>
<text x="1100" y="570" fill="#f7f7f7" font-family="Arial, sans-serif" font-size="62" font-weight="bold">{b['detected']}/{b['total']} → {a['detected']}/{a['total']}</text>
<text x="1100" y="610" fill="#a6a6a6" font-family="monospace" font-size="15">FINAL AUDIT DEFECTS CAUGHT</text>
<text x="75" y="725" fill="#f5f5f5" font-family="monospace" font-size="16">ATTACK → REPRODUCE → IMPROVE → AUDIT</text>
<text x="75" y="760" fill="#8f8f8f" font-family="monospace" font-size="13">{html.escape(r['manifest']['mode'].upper())} · SYNTHETIC BENCHMARK · ALL RESULTS PUBLISHED</text>
<text x="1100" y="725" fill="#acacac" font-family="monospace" font-size="15">github.com/KaushikSiva/crossexam</text>
</svg>'''
(out/"banner.svg").write_text(banner)
architecture='''<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="650" viewBox="0 0 1500 650">
<rect width="1500" height="650" fill="#f7f7f7"/>
<text x="65" y="75" font-family="Arial" font-size="34" font-weight="bold" fill="#171717">Separate contexts. Executable judgment.</text>
<text x="65" y="114" font-family="Arial" font-size="18" fill="#7a7a7a">Models propose. The contract and sandboxed execution decide.</text>
<defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8" fill="none" stroke="#929292"/></marker></defs>
<g fill="none" stroke="#929292" stroke-width="2" marker-end="url(#a)"><path d="M325 260H365"/><path d="M625 260H665"/><path d="M925 260H965"/><path d="M1225 260H1260"/><path d="M795 340V410H495V340"/></g>
<g font-family="Arial" fill="#171717">
<rect x="65" y="180" width="260" height="160" fill="#ebebeb"/><text x="85" y="213" font-size="12" fill="#717171">SUBQUADRATIC / RISK ROUTER</text><text x="85" y="254" font-size="25">Where to look</text><text x="85" y="289" font-size="16">Contract + repository + tests</text><text x="85" y="314" font-size="16">Typed risk decisions</text>
<rect x="365" y="180" width="260" height="160" fill="#ebebeb"/><text x="385" y="213" font-size="12" fill="#717171">META / ADVERSARIAL CONTEXT</text><text x="385" y="254" font-size="25">Find a blind spot</text><text x="385" y="289" font-size="16">Propose a faulty implementation</text><text x="385" y="314" font-size="16">Must pass the existing tests</text>
<rect x="665" y="180" width="260" height="160" fill="#111111"/><text x="685" y="213" font-size="12" fill="#f5f5f5">ISOLATED EXECUTION</text><text x="685" y="254" font-size="25" fill="#f7f7f7">Prove the failure</text><text x="685" y="289" font-size="16" fill="#cccccc">Independent event-ledger oracle</text><text x="685" y="314" font-size="16" fill="#cccccc">Minimize the failing sequence</text>
<rect x="965" y="180" width="260" height="160" fill="#ebebeb"/><text x="985" y="213" font-size="12" fill="#717171">META / FRESH TEST CONTEXT</text><text x="985" y="254" font-size="25">Strengthen the eval</text><text x="985" y="289" font-size="16">Contract + observed failures</text><text x="985" y="314" font-size="16">Implementation withheld</text>
<text x="1285" y="241" font-size="21">Freeze</text><text x="1285" y="272" font-size="21">Validate</text><text x="1285" y="303" font-size="21">Promote</text>
<text x="550" y="445" font-size="14" fill="#7a7a7a">Only demonstrated failures become evidence.</text>
<path d="M65 490H1435" stroke="#cfcfcf" stroke-dasharray="5 6"/>
<text x="65" y="535" font-size="13" fill="#7a7a7a">SEPARATE FINAL AUDIT</text><text x="65" y="575" font-size="23">Opened after learning ends. Never sent back to either model.</text>
<text x="1000" y="535" font-size="13" fill="#7a7a7a">PROMOTION GATE</text><text x="1000" y="575" font-size="18">More defects caught. No lost coverage.</text><text x="1000" y="606" font-size="18">No correct implementation rejected.</text>
</g></svg>'''
(out/"architecture.svg").write_text(architecture)
live=r["manifest"]["mode"]=="live partners"
subq=r["manifest"]["mode"].startswith("live Subquadratic")
parts=[
 "Meet CrossExam. It finds broken software that your tests accept, then proves whether stronger evaluations actually help.",
 "Here, all four tests pass. But an optimization drops the tenant from the cache key. Two customers reuse the same request ID, and the second gets the first customer's reservation. CrossExam reduces the failure to two requests.",
 "The eval improves through versioned proposals. Each suite is frozen, then challenged on separate validation defects and correct implementations. Only measured gains earn promotion. A deliberately weakened suite is rejected.",
 f"Now the final audit opens. Detection rises from {b['detected']} of {b['total']} defects to {a['detected']} of {a['total']}, with {a['false_rejections']} correct controls rejected. Every result, including remaining misses, is published.",
 ("Meta generates attacks and independent tests. Subquadratic prioritizes risks. OpenUI makes the evidence interactive. Every provider call is recorded." if live else "Subquadratic prioritizes risks from repository context. This run uses local attack and test fixtures. OpenUI makes every result inspectable." if subq else "OpenUI turns the recorded results into interactive evidence. This local benchmark uses fixtures; live partner integrations are labeled separately."),
 "CrossExam. Your tests passed. Your software failed. Here is the evidence."
]
(out/"narration.json").write_text(json.dumps({"mode":r["manifest"]["mode"],"segments":parts,"words":sum(len(p.split()) for p in parts)},indent=2))
print('Artwork and narration prepared:',sum(len(p.split()) for p in parts),'words')
