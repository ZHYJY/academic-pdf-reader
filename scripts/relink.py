#!/usr/bin/env python3
"""Reconcile figure/table mentions with caption lines and page-level evidence."""
import json,re,sys
from pathlib import Path
CAP=re.compile(r"^\s*(?:(Figure|Fig\.?|Table)\s*(\d+[a-z]?))\s*[:.\-]\s*(.+)",re.I)
REF=re.compile(r"\b(Figure|Fig\.?|Table)\s*(\d+[a-z]?)\b",re.I)
def key(kind,num):return ("table" if kind.lower().startswith("table") else "figure",num.lower())
def main():
    d=Path(sys.argv[1]);md=(d/"paper.md").read_text(encoding="utf-8")
    pages=re.split(r"<!-- page:\s*(\d+)\s*-->",md)
    caps=[];refs=[]
    for j in range(1,len(pages),2):
        page=int(pages[j]);text=pages[j+1].split("![Original page")[0]
        for line in text.splitlines():
            c=CAP.match(line)
            if c:
                caps.append({"kind":key(c[1],c[2])[0],"number":c[2].lower(),"caption":c[3].strip(),
                             "page":page,"evidence":f"assets/page-{page:04d}.png"})
                continue
            for m in REF.finditer(line):
                refs.append({"kind":key(m[1],m[2])[0],"number":m[2].lower(),"source_page":page,
                             "context":line.strip()[:500]})
    for r in refs:
        matches=[c for c in caps if (c["kind"],c["number"])==(r["kind"],r["number"])]
        r["targets"]=matches;r["status"]="matched" if len(matches)==1 else "ambiguous" if matches else "unresolved"
    out={"captions":caps,"references":refs,"unresolved":sum(r["status"]!="matched" for r in refs)}
    (d/"evidence_links.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"captions":len(caps),"references":len(refs),"unresolved":out["unresolved"]}))
if __name__=="__main__":main()
