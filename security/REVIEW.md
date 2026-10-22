# Security review and deployment checklist

Review scope: bundled source manually structured and Python AST-checked. No comprehensive third-party source audit, SBOM scan, malware scan, or penetration test has been performed.

[ ] Lock PyMuPDF, Docling and all transitive dependencies to reviewed hashes.
[ ] Review exact Docling commit/release and model files; verify model hashes and license.
[ ] Run under non-root, network-disabled container/VM, read-only PDF mount, no credentials.
[ ] Limit CPU, RAM, disk, file count, page count and wall time.
[ ] Keep offline flags; block network at OS level, not only via environment.
[ ] Test malformed, encrypted, malicious and oversized PDFs.
[ ] Prevent symlink/path escape in output directory at deployment boundary.
[ ] Maintain regression corpus and human-annotated ground truth before production certification.

Known risk: parser vulnerabilities and local model runtime behavior cannot be excluded by this checklist.
