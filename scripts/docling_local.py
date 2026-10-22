#!/usr/bin/env python3
"""Offline-only Docling adapter; requires preinstalled, audited Docling and cached models."""
import argparse,json,os,sys
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument("pdf");p.add_argument("--out",required=True)
    a=p.parse_args()
    for key in ("HF_HUB_OFFLINE","TRANSFORMERS_OFFLINE","HF_DATASETS_OFFLINE"):
        if os.environ.get(key)!="1":p.error(f"{key}=1 required")
    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
    except ImportError as e:
        print(f"Docling not installed: {e}",file=sys.stderr);sys.exit(3)
    opts=PdfPipelineOptions()
    opts.do_table_structure=True
    opts.do_formula_enrichment=True
    # Models must already be cached; Docling version must be pinned and reviewed.
    if os.environ.get("DOCLING_ARTIFACTS_PATH"):
        opts.artifacts_path=os.environ["DOCLING_ARTIFACTS_PATH"]
    converter=DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=opts)})
    result=converter.convert(a.pdf)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    (out/"document.md").write_text(result.document.export_to_markdown(),encoding="utf-8")
    (out/"document.json").write_text(result.document.model_dump_json(indent=2),encoding="utf-8")
    (out/"status.json").write_text(json.dumps({"status":"EXTRACTED_UNVERIFIED",
       "formula_enrichment_requested":True,"table_structure_requested":True,
       "note":"No independent formula/table ground-truth verification"}),encoding="utf-8")
    print(json.dumps({"status":"EXTRACTED_UNVERIFIED","output":str(out)}))
if __name__=="__main__":main()
