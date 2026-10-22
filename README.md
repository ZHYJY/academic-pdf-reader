# Academic PDF Reader v4.0 (research-grade candidate)

## Execution
Python 3.10+, reviewed PyMuPDF. Optional: reviewed/pinned Docling + model artifacts prepared separately by administrator. Do not run unknown PDFs outside a network-disabled OS sandbox.

Baseline:
`python scripts/pipeline.py /papers/paper.pdf --allowed-root /papers --out /results/paper --engine baseline`

Enhanced (requires offline Docling models):
`HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 DOCLING_ARTIFACTS_PATH=/models/docling python scripts/pipeline.py /papers/paper.pdf --allowed-root /papers --out /results/paper --engine docling`

On-demand figure evidence:
`python scripts/visual_request.py /results/paper --figure 3 --question "What does the plot show?"`

Regression:
`python tests/regression.py`

**Limitations:** Docling adapter is optional and requires pinned, locally cached models. No cloud VLM calls. Automated QA checks artifacts, not scientific fidelity. This package is not certified for unattended publication-grade extraction.
