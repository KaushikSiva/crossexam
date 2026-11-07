"""Export one completed run for a public, read-only evidence viewer."""

import argparse
import json
from pathlib import Path
import shutil

parser=argparse.ArgumentParser()
parser.add_argument("run",type=Path)
parser.add_argument("--out",type=Path,default=Path("docs"))
args=parser.parse_args()
report=json.loads((args.run/"report.json").read_text())
root=Path(__file__).resolve().parent.parent
args.out.mkdir(parents=True,exist_ok=True)
for name in ("index.html","style.css","app.js","favicon.svg"):
    shutil.copy2(root/"web"/name,args.out/name)
(args.out/"report.json").write_text(json.dumps(report,indent=2))
(args.out/".nojekyll").touch()
evidence=args.out/"evidence"/args.run.name
if evidence.exists():
    raise SystemExit(f"Refusing to overwrite existing evidence: {evidence}")
shutil.copytree(args.run,evidence)
print(f"Exported {report['manifest']['mode']} evidence to {args.out}")
