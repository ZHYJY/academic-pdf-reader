#!/usr/bin/env python3
"""Select page evidence for approved, on-demand vision review. No network/model invocation."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("out");p.add_argument("--figure",required=True)
p.add_argument("--question",required=True);a=p.parse_args()
d=Path(a.out);links=json.loads((d/"evidence_links.json").read_text())
num=a.figure.lower().replace("figure","").replace("fig.","").replace("fig","").strip()
targets=[c for c in links["captions"] if c["kind"]=="figure" and c["number"]==num]
packet={"figure":a.figure,"question":a.question,"status":"READY" if len(targets)==1 else "AMBIGUOUS_OR_MISSING",
        "evidence":targets,"model_invoked":False,"network_invoked":False,
        "instructions":"Inspect only locally with approved vision tool; distinguish visible facts from inferences; no precise chart data invention."}
print(json.dumps(packet,ensure_ascii=False,indent=2))
