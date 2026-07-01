# arXiv submission — The RTL Gauntlet

**Ready to upload:** `arxiv-submission.tar.gz` — self-contained (`main.tex` + `figures/`).

## Package contents
- `main.tex` — single source; references are a manual `thebibliography` (no BibTeX, no `.bbl` step).
- `figures/{progression,models,cost}.pdf` — the three matplotlib figures. Figure 1 is inline TikZ.

## Verified in this build
- ✅ `\pdfoutput=1` on line 1 → arXiv selects **pdfLaTeX** (required because figures are PDF).
- ✅ Compiles in an **isolated clean dir** (only `main.tex` + `figures/`) → **8 pages, 0 errors, 0 missing files**.
- ✅ No BibTeX, no shell-escape / `\write18`, no external `\input` — nothing arXiv can't resolve.
- ✅ PDF metadata embedded (title / author / keywords; check with `pdfinfo main.pdf`).
- ✅ Fonts T1 + `lmodern` (vector, no bitmaps); `microtype` on.
- ✅ Overfull boxes cleaned — only one residual 0.30 pt (≈0.004 in, sub-visible).

## Build locally
```bash
cd paper
latexmk -pdf main.tex      # settles floats/refs; or run: pdflatex main.tex  (×3)
```

## Re-pack the tarball after any edit
```bash
cd paper
rm -rf /tmp/arxiv_pkg && mkdir -p /tmp/arxiv_pkg/figures
cp main.tex /tmp/arxiv_pkg/ && cp figures/*.pdf /tmp/arxiv_pkg/figures/
( cd /tmp/arxiv_pkg && tar czf "$OLDPWD/arxiv-submission.tar.gz" main.tex figures )
```

## On the arXiv upload form
- **Engine:** pdfLaTeX (auto-detected from `\pdfoutput=1`).
- **Primary category:** `cs.AR` (Hardware Architecture). **Cross-list:** `cs.LG`, `cs.SE` (optionally `cs.AI`).
- **License:** `CC BY 4.0` recommended (benchmark/artifact — lets others build on it).
- **Authorship:** named — Vuong Tran Dinh Minh, Independent Researcher.

## Pre-submission checks (do yourself)
- [ ] Make the linked repo **public** before submitting: <https://github.com/loversky02/rtl-gauntlet>
- [ ] Sanity-check the arXiv IDs/years in `thebibliography` are correct (several cite very recent work).
- [ ] Open `main.pdf` once more: title page, Figure 1 boxes, Table 3 (5 models), no stray gaps.
