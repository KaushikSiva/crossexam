"""Copy landing source into the public repository; exclude hosting identity/secrets."""

import argparse
from pathlib import Path
import shutil

parser=argparse.ArgumentParser()
parser.add_argument('source',type=Path)
args=parser.parse_args()
root=Path(__file__).resolve().parent.parent
target=root/'site';target.mkdir(exist_ok=True)
for name in ('src','public'):
    shutil.copytree(args.source/name,target/name,dirs_exist_ok=True)
for name in ('package.json','package-lock.json','vite.config.js','index.html','DESIGN.md','.gitignore'):
    shutil.copy2(args.source/name,target/name)
print('Copied landing source without Sites identity, credentials, or Git metadata.')
