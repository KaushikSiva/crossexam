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
protocol=r['manifest'].get('proposal_protocol',{})
names={'openai':'OpenAI','meta':'Meta Muse Spark','gemini':'Gemini','fetchai':'Fetch.ai ASI:One','fixtures':'seeded fixtures'}
attacker=names.get(protocol.get('generator'),'the selected provider')
architecture=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="780" viewBox="0 0 1500 780">
<rect width="1500" height="780" fill="#ededed"/>
<g font-family="Arial, sans-serif" fill="#171717">
<text x="65" y="60" font-size="13" letter-spacing="2" fill="#777">CROSSEXAM / ARCHITECTURE</text>
<text x="65" y="130" font-size="48" font-weight="bold">Muse at the core. Execution as the judge.</text>
<text x="65" y="175" font-size="21" fill="#777">Models propose. Independent tests and sandboxed execution decide.</text>
<path d="M65 215H1435M65 595H1435" stroke="#c8c8c8"/>
<text x="65" y="260" font-size="13" fill="#777">PRIMARY CODE-GENERATION INTEGRATION</text>
<text x="65" y="320" font-size="31">Meta</text><text x="65" y="385" font-size="65" font-weight="bold">Muse Spark</text>
<text x="65" y="435" font-size="21">Propose adversarial implementations.</text><text x="65" y="468" font-size="21">Challenge what passing tests really prove.</text>
<text x="65" y="525" font-size="15" fill="#666">Adapter implemented. API access currently returns HTTP 402.</text>
<path d="M640 245V555" stroke="#c8c8c8"/>
<text x="700" y="262" font-size="13" fill="#777">INDEPENDENT TEST AUTHOR</text><text x="700" y="300" font-size="30">Google DeepMind / Gemini</text><text x="700" y="330" font-size="18" fill="#666">Contract + counterexamples. Candidate code withheld.</text>
<text x="700" y="375" font-size="13" fill="#777">CALLABLE VERIFICATION</text><text x="700" y="413" font-size="30">Fetch.ai / uAgents</text><text x="700" y="443" font-size="18" fill="#666">Execute a patch. Return a cryptographically signed verdict.</text>
<text x="700" y="488" font-size="13" fill="#777">EVIDENCE AND FROZEN SUITES</text><text x="700" y="526" font-size="30">MongoDB</text><text x="700" y="556" font-size="18" fill="#666">Hash-verified artifacts, suite versions and signed receipts.</text>
<text x="65" y="640" font-size="18">Subquadratic prioritizes risks</text><text x="515" y="640" font-size="18">OS sandbox + independent oracle</text><text x="1060" y="640" font-size="18">OpenUI exposes the evidence</text>
<text x="65" y="706" font-size="16" fill="#666">Recorded campaign: {html.escape(attacker)} generated the patch. Muse access awaits credits.</text>
<text x="65" y="739" font-size="16" fill="#666">Freeze → validate → promote → separate final audit. Every decision retains its evidence.</text>
</g></svg>'''
(out/"architecture.svg").write_text(architecture)
validation=r['validation_after']
generated=next((c for c in r['counterexamples'] if c['id']=='M01'),r['counterexamples'][0])
requests=len(generated['witness']['actions'])
parts=[
    "Every test passed. Would you ship it? CrossExam challenges the tests behind that confidence.",
    f"This {'generated' if generated['id']=='M01' else 'seeded'} patch passes all four tests. {requests} requests expose a real contract violation.",
    "Muse Spark is our primary code-generation integration. Gemini writes independent tests. Subquadratic prioritizes risks. This run uses ASI One while Muse awaits credits.",
    f"Gemini raises validation detection from {r['validation_before']['detected']} to {validation['detected']} out of {validation['total']}. Only measured improvements are promoted.",
    f"Freeze the suite. The separate audit catches {a['detected']} of {a['total']} faulty implementations. All {a['controls']} correct implementations pass. This is a public synthetic benchmark.",
    "Fetch agents load the frozen suite from MongoDB. Broken patch blocked. Correct code accepted. Both verdicts cryptographically signed.",
    "CrossExam. Make passing tests earn your trust."
]
(out/"narration.json").write_text(json.dumps({"mode":r["manifest"]["mode"],"segments":parts,"words":sum(len(p.split()) for p in parts)},indent=2))
print('Artwork and narration prepared:',sum(len(p.split()) for p in parts),'words')
