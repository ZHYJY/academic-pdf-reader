#!/usr/bin/env python3
"""Local, evidence-preserving academic PDF baseline; PyMuPDF only."""
import argparse, csv, hashlib, json, re
from pathlib import Path
import fitz

REF = re.compile(r"\b(?:Fig(?:ure)?s?\.?|Tables?)\s*(\d+[a-z]?)",re.I)
CAP = re.compile(r"^\s*((?:Fig(?:ure)?\.?|Table)\s*\d+[a-z]?)\s*[:.\-]?\s*(.*)",re.I)
EQU = re.compile(r"(?:[=∑∫√≤≥≈∂∇]|\\(?:frac|sum|int|alpha|beta)|\b(?:where|denotes|defined as)\b)",re.I)
NUM = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
def typed(s):
    if s is None: return None
    v=str(s).strip().replace(",","")
    if NUM.fullmatch(v):
        try: return float(v) if ('.' in v or 'e' in v.lower()) else int(v)
        except ValueError: pass
    return None
def mdcell(s):
    return str(s or "").replace("|",r"\|").replace("\n"," ").strip()
def save_table(rows,stem,folder):
    rows=[[None if v is None else str(v) for v in row] for row in rows]
    width=max((len(r) for r in rows),default=0)
    rows=[r+[None]*(width-len(r)) for r in rows]
    csvpath=folder/(stem+".csv")
    with csvpath.open("w",newline="",encoding="utf-8-sig") as f:
        csv.writer(f).writerows([["" if v is None else v for v in row] for row in rows])
    obj={"raw_rows":rows,"numeric_values":[[typed(v) for v in row] for row in rows],
         "warning":"Numeric values are inferred conservatively; table structure and merged cells unverified."}
    (folder/(stem+".json")).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
    if width:
        head="| "+" | ".join(mdcell(v) for v in rows[0])+" |"
        sep="| "+" | ".join("---" for _ in range(width))+" |"
        body=["| "+" | ".join(mdcell(v) for v in row)+" |" for row in rows[1:]]
        md="\n".join([head,sep]+body)+"\n"
    else: md="(No recoverable cells)\n"
    (folder/(stem+".md")).write_text(md,encoding="utf-8")
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("pdf"); ap.add_argument("--allowed-root",required=True)
    ap.add_argument("--out",required=True); ap.add_argument("--max-mb",type=int,default=100)
    ap.add_argument("--max-pages",type=int,default=500)
    ap.add_argument("--dpi",type=int,default=120)
    args=ap.parse_args()
    src=Path(args.pdf)
    if src.is_symlink() or not src.is_file() or src.suffix.lower()!=".pdf": ap.error("Require regular non-symlink PDF")
    src=src.resolve(strict=True); allowed=Path(args.allowed_root).resolve(strict=True)
    if not src.is_relative_to(allowed): ap.error("PDF outside allowed root")
    if src.stat().st_size>args.max_mb*1024*1024: ap.error("File too large")
    with src.open("rb") as f:
        if f.read(5)!=b"%PDF-": ap.error("Invalid PDF signature")
    if not 72<=args.dpi<=200: ap.error("DPI must be 72..200")
    out=Path(args.out).resolve()
    if out==src or out.is_relative_to(src) or out.exists(): ap.error("Output directory must not exist")
    # Validate PDF before creating output.
    with fitz.open(src) as d:
        if d.needs_pass: ap.error("Encrypted PDF")
        if len(d)>args.max_pages: ap.error("Page limit exceeded")
    (out/"assets").mkdir(parents=True); (out/"tables").mkdir()
    sha=hashlib.file_digest(src.open("rb"),"sha256").hexdigest()
    manifest={"version":"3.0.0","source_sha256":sha,"parser":"PyMuPDF",
              "parser_version":fitz.VersionBind,"pages":[],"tables":[],"rasters":[],"warnings":[]}
    markdown=[]; captions=[]; refs=[]; equations=[]
    with fitz.open(src) as doc:
        for n,page in enumerate(doc,1):
            png=f"assets/page-{n:04d}.png"
            page.get_pixmap(matrix=fitz.Matrix(args.dpi/72,args.dpi/72),alpha=False).save(str(out/png))
            text=page.get_text("text",sort=True)
            markdown.append(f"<!-- page: {n} -->\n\n{text}\n\n![Original page {n}]({png})\n")
            for line in text.splitlines():
                c=CAP.match(line)
                if c: captions.append({"label":c.group(1),"text":c.group(2).strip(),"page":n,"evidence":png})
                for m in REF.finditer(line):
                    refs.append({"reference":m.group(0),"number":m.group(1),"kind":"table" if m.group(0).lower().startswith("table") else "figure","page":n})
                if EQU.search(line) and len(line)<240:
                    equations.append({"page":n,"raw_text":line.strip(),"latex":None,"status":"candidate_unverified","evidence":png})
            page_tables=[]
            try:
                for k,t in enumerate(page.find_tables().tables,1):
                    stem=f"table-p{n:04d}-{k:02d}"
                    bbox=fitz.Rect(t.bbox)
                    crop=f"assets/{stem}.png"
                    page.get_pixmap(matrix=fitz.Matrix(args.dpi/72,args.dpi/72),clip=bbox,alpha=False).save(str(out/crop))
                    rows=t.extract()
                    save_table(rows,stem,out/"tables")
                    item={"id":stem,"page":n,"bbox":list(bbox),"image":crop,
                          "csv":f"tables/{stem}.csv","json":f"tables/{stem}.json",
                          "markdown":f"tables/{stem}.md","rows":len(rows),
                          "status":"structure_unverified"}
                    manifest["tables"].append(item); page_tables.append(item)
                    markdown.append(f"\nTable evidence, page {n}: ![{stem}]({crop})\n\n"
                                    f"Structured candidate: [{stem}](tables/{stem}.md)\n")
            except Exception as e: manifest["warnings"].append(f"Page {n}: table detection failed: {type(e).__name__}")
            # Embedded raster images are evidence only; vector graphics stay in page image.
            images=[]
            try:
                for k,img in enumerate(page.get_images(full=True),1):
                    xref=img[0]; data=doc.extract_image(xref)
                    ext=data.get("ext","bin")
                    if ext not in ("png","jpeg","jpg","webp"): continue
                    name=f"assets/raster-p{n:04d}-{k:02d}.{ext}"
                    (out/name).write_bytes(data["image"])
                    images.append(name)
                    manifest["rasters"].append({"page":n,"path":name,"xref":xref})
            except Exception as e: manifest["warnings"].append(f"Page {n}: raster extraction failed: {type(e).__name__}")
            if len(text.strip())<100: manifest["warnings"].append(f"Page {n}: low text coverage; OCR review needed")
            manifest["pages"].append({"page":n,"text_characters":len(text.strip()),
                                      "page_image":png,"table_ids":[t["id"] for t in page_tables],
                                      "raster_paths":images})
    links=[]
    for r in refs:
        expected=f"{'Table' if r['kind']=='table' else 'Figure'} {r['number']}"
        matches=[c for c in captions if re.sub(r"\W","",c["label"]).lower() in
                 (re.sub(r"\W","",expected).lower(),
                  re.sub(r"\W","",f"Fig {r['number']}").lower())]
        links.append({**r,"status":"matched_caption" if len(matches)==1 else ("ambiguous" if matches else "unresolved"),
                      "targets":matches})
    (out/"paper.md").write_text("\n".join(markdown),encoding="utf-8")
    (out/"equations.json").write_text(json.dumps(equations,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"links.json").write_text(json.dumps({"captions":captions,"references":links},ensure_ascii=False,indent=2),encoding="utf-8")
    n_pages=len(manifest["pages"])
    missing=[p["page"] for p in manifest["pages"] if not (out/p["page_image"]).exists()]
    missing_tables=[t["id"] for t in manifest["tables"] if not all((out/t[k]).exists() for k in ("image","csv","json","markdown"))]
    unresolved=[r for r in links if r["status"]!="matched_caption"]
    qa={"status":"PARTIAL_REVIEW_REQUIRED","pages":n_pages,"page_images_present":n_pages-len(missing),
        "missing_page_images":missing,"tables_detected":len(manifest["tables"]),
        "table_artifacts_missing":missing_tables,"equation_candidates":len(equations),
        "unresolved_or_ambiguous_references":len(unresolved),
        "reference_section_keyword_found":bool(re.search(r"(?im)^\s*(references|bibliography)\s*$","\n".join(markdown))),
        "limitations":["No independent visual comparison performed",
                       "Vector figures are preserved in full-page images but not segmented",
                       "Complex tables, equations and multi-column order need review",
                       "Reference list completeness not verified",
                       "No OCR or VLM called"]}
    (out/"qa_report.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding="utf-8")
    manifest["qa_status"]=qa["status"]
    (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":qa["status"],"pages":n_pages,"tables":len(manifest["tables"]),
                      "unresolved_links":len(unresolved),"output":str(out)},ensure_ascii=False))
if __name__=="__main__": main()
