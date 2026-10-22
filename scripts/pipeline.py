#!/usr/bin/env python3
"""Run baseline and optional local Docling; never downloads intentionally."""
import argparse, json, os, subprocess, sys
from pathlib import Path
def run(cmd, env):
    p=subprocess.run(cmd,env=env,check=False,text=True,capture_output=True)
    return {"returncode":p.returncode,"stdout":p.stdout[-3000:],"stderr":p.stderr[-3000:]}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("pdf");p.add_argument("--allowed-root",required=True)
    p.add_argument("--out",required=True);p.add_argument("--engine",choices=["baseline","docling"],default="baseline")
    p.add_argument("--max-pages",type=int,default=500);p.add_argument("--max-mb",type=int,default=100)
    a=p.parse_args();here=Path(__file__).resolve().parent
    env=dict(os.environ,HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_DATASETS_OFFLINE="1",
             DOCLING_ARTIFACTS_PATH=os.environ.get("DOCLING_ARTIFACTS_PATH",""))
    output=Path(a.out).resolve()
    base=run([sys.executable,str(here/"baseline.py"),a.pdf,"--allowed-root",a.allowed_root,
              "--out",str(output),"--max-pages",str(a.max_pages),"--max-mb",str(a.max_mb)],env)
    if base["returncode"]:
        print(json.dumps({"status":"FAILED_BASELINE","baseline":base},ensure_ascii=False));sys.exit(1)
    enrich=None
    if a.engine=="docling":
        enrich=run([sys.executable,str(here/"docling_local.py"),a.pdf,"--out",str(output/"docling")],env)
    link=run([sys.executable,str(here/"relink.py"),str(output)],env)
    qa=run([sys.executable,str(here/"qa.py"),str(output),"--requested-engine",a.engine],env)
    status="ENHANCED_REVIEW_REQUIRED" if a.engine=="docling" and enrich and enrich["returncode"]==0 else "BASELINE_REVIEW_REQUIRED"
    if a.engine=="docling" and enrich["returncode"]!=0:status="DEGRADED_DOCLING_UNAVAILABLE"
    if qa["returncode"]:status="FAILED_QA"
    report={"status":status,"requested_engine":a.engine,"baseline":base,"enhancement":enrich,"linking":link,"qa":qa}
    (output/"pipeline_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":status,"output":str(output)},ensure_ascii=False))
    if status in ("FAILED_QA","DEGRADED_DOCLING_UNAVAILABLE"):sys.exit(2)
if __name__=="__main__":main()
