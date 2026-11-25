# IEEE OJVT draft

Build: `latexmk -pdf -interaction=nonstopmode main.tex` (from this directory).

- Numbers: `python src/paper_numbers.py` (repo root) writes `paper/numbers.tex` from `results/*.csv`. Never type a number into the text.
- Figures: `python src/figures.py --out results/figures`; `main.tex` includes them from `results/figures/`.
- All results: `python src/reproduce.py --estimator ~/blur_study --data ~/sd_data --scratch ~/sd_work/m9` (on the machine with the caches).
- Template: official IEEE OJVT LaTeX template (`ieee-ojvt.cls` and `ojvt-logo.png`, dated 2024-06-27, from the IEEE Template Selector), with `IEEEtran.bst` for references. Front-matter dates and DOI are placeholders filled by IEEE.
- OJVT rules checked 2026-11: up to 14 pages for a new submission, single-anonymous review, ORCID for all authors, abstract 150-250 words in one paragraph, AI-tool use disclosed in the acknowledgment.
- Blue `[...]` notes mark text still to write. Subset results (M2, M3) are replaced by the full Phase 2 render when it is scored.
- References come from `docs/litreview/LITERATURE_REVIEW.md` (metadata checked against Crossref there).
