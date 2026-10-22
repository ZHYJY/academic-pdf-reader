#!/usr/bin/env python3
"""Deterministic regression fixtures. Not a substitute for real annotated academic corpus."""
import json, subprocess, sys, tempfile
from pathlib import Path
import fitz
SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
def fixture(path,kind):
    d=fitz.open()
    if kind=="two_column":
        p=d.new_page()
        p.insert_text((45,45),"A two-column academic study",fontsize=16)
        p.insert_textbox(fitz.Rect(45,75,275,400),"LEFT COLUMN " * 35,fontsize=10)
        p.insert_textbox(fitz.Rect(310,75,540,400),"RIGHT COLUMN " * 35,fontsize=10)
        p.insert_text((45,450),"Figure 2: Example plot caption")
        p.draw_polyline([(60,530),(130,490),(210,510)],color=(0,0,0))
    elif kind=="table":
        p=d.new_page();p.insert_text((45,45),"Table 1: Ablation results")
        for x in (45,175,300,440):
            p.draw_line((x,80),(x,180))
        for y in (80,110,145,180):
            p.draw_line((45,y),(440,y))
        for x,y,s in [(55,99,"Method"),(185,99,"Accuracy"),(310,99,"F1"),
                      (55,132,"Baseline"),(185,132,"0.82"),(310,132,"0.78"),
                      (55,165,"Improved"),(185,165,"0.91"),(310,165,"0.89")]:
            p.insert_text((x,y),s,fontsize=10)
        p.insert_text((45,210),"As shown in Table 1, results improved.")
    elif kind=="equations":
        p=d.new_page();p.insert_text((45,45),"Equation study")
        p.insert_text((45,90),"E = m c^2")
        p.insert_text((45,120),"where m denotes mass")
        p.insert_text((45,160),"References")
        p.insert_text((45,185),"[1] Synthetic bibliography item")
        p2=d.new_page();p2.insert_text((45,50),"Appendix A: Proof")
        p2.insert_text((45,90),"x = y + 2")
    d.save(str(path));d.close()
def main():
    results=[]
    with tempfile.TemporaryDirectory() as temp:
        td=Path(temp)
        for kind in ("two_column","table","equations"):
            pdf=td/(kind+".pdf");fixture(pdf,kind)
            out=td/(kind+"-out")
            p=subprocess.run([sys.executable,str(SCRIPTS/"pipeline.py"),str(pdf),
                 "--allowed-root",str(td),"--out",str(out)],capture_output=True,text=True)
            if p.returncode: raise AssertionError(f"{kind} failed: {p.stderr[-800:]} {p.stdout[-800:]}")
            qa=json.loads((out/"quality_gate.json").read_text())
            manifest=json.loads((out/"manifest.json").read_text())
            assert qa["status"]=="PASS_ARTIFACTS_ONLY"
            assert qa["pages"]==len(manifest["pages"])
            assert all((out/x["page_image"]).is_file() for x in manifest["pages"])
            assert (out/"paper.md").is_file()
            if kind=="table":
                assert len(manifest["tables"])>=1,"Synthetic bordered table was not detected"
                t=manifest["tables"][0]
                assert (out/t["csv"]).is_file() and (out/t["image"]).is_file()
            if kind=="two_column":
                packet=subprocess.run([sys.executable,str(SCRIPTS/"visual_request.py"),str(out),
                    "--figure","2","--question","What does the figure show?"],capture_output=True,text=True)
                assert packet.returncode==0
                assert json.loads(packet.stdout)["status"]=="READY"
            results.append({"fixture":kind,"status":"PASS","pages":qa["pages"],
                            "tables":qa["tables_detected"],"unresolved_links":qa["unresolved_figure_table_links"]})
    print(json.dumps({"status":"PASS","synthetic_regressions":results,
      "caveat":"Synthetic fixture tests only; no real-paper fidelity benchmark or Docling model evaluation"},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
