# IEEE OJVT draft (skeleton)

Build: `latexmk -pdf -interaction=nonstopmode main.tex` (from this directory).

- Numbers: `python src/paper_numbers.py` (repo root) writes `paper/numbers.tex` from `results/*.csv`. Never type a number into the text.
- Figures: `python src/figures.py --out results/figures`; `main.tex` includes them from `results/figures/`.
- All results: `python src/reproduce.py --estimator ~/blur_study --data ~/sd_data --scratch ~/sd_work/m9` (on the machine with the caches).
- Template: IEEEtran journal class for now. Swap to the official IEEE Open Journal (OJVT) template and check the current author instructions before submission.
- Blue `[...]` notes mark text still to write. Subset results (M2, M3) are replaced by the full Phase 2 render when it is scored.
- References come from `docs/litreview/LITERATURE_REVIEW.md` (metadata checked against Crossref there).
