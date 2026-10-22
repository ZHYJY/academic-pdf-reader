#!/usr/bin/env python3
"""Hard artifact invariants, not a ground-truth fidelity certification."""
import argparse,json,re,sys
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument("out");p.add_argument("--requested-engine",choices=["baseline","docling"],default="baseline")
    a=p.parse_args();d=Path(a.out)
    m=json.loads((d/"manifest.json").read_text());links=json.loads((d/"evidence_links.json").read_text())
    missing=[x["page_image"] for x in m["pages"] if not (d/x["page_image"]).is_file()]
    for t in m["tables"]:
        missing += [t[k] for k in ("image","csv","json","markdown") if not (d/t[k]).is_file()]
    enhanced=(d/"docling"/"document.md").is_file() and (d/"docling"/"document.json").is_file()
    if a.requested_engine=="docling" and not enhanced:missing.append("docling/document.md or .json")
    status="FAIL" if missing or len(m["pages"])==0 else "PASS_ARTIFACTS_ONLY"
    report={"status":status,"pages":len(m["pages"]),"missing_artifacts":missing,
            "tables_detected":len(m["tables"]),"unresolved_figure_table_links":links["unresolved"],
            "docling_enhanced_output_present":enhanced,
            "scientific_fidelity_verified":False,
            "manual_review_required":["formula correctness","complex table structure","reading order",
              "vector figure segmentation","bibliography completeness","OCR/scanned pages"]}
    (d/"quality_gate.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
    if status=="FAIL":sys.exit(2)
if __name__=="__main__":main()
