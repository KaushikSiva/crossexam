"""Copied into the candidate sandbox. Receives inputs; never expected outputs."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from service import Service

for line in sys.stdin:
    actions = json.loads(line)
    service = Service()
    responses = []
    for action in actions:
        try:
            responses.append(service.handle(action))
        except Exception as exc:
            responses.append({"_exception": type(exc).__name__})
    print(json.dumps(responses, allow_nan=False), flush=True)
