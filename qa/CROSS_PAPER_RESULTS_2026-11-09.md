# SharePack cross-paper QA: scVI & Celina (2026-11-09)

## Scope and integrity

- **Project baseline:** `main` commit `0caea5796ce7d9f958eb70e8fddaa5742cd206c7`; experiments run separately on branch `qa/celina-crosspaper-20261109`.
- **No change to `main`, `v0.1.0-rc.1`, original ten-card artifacts, PFS main repository, or existing releases.**
- **Scientific panels were not uploaded as artifacts.** The tests use authentic PDFs/candidate crops locally on ephemeral GitHub Actions runners; no adapted paper graphics were published.
- The reports below are limited to engineering behavior. There has been **no full scientific or mobile visual acceptance**.

## Probe A — Celina

- Shang, Wu & Zhou, *Statistical identification of cell type-specific spatially variable genes in spatial transcriptomics*, Nature Communications 16, 1059 (2025), DOI: [10.1038/s41467-025-56280-4](https://doi.org/10.1038/s41467-025-56280-4).
- Source license: **CC BY-NC-ND 4.0**; figure derivatives were not redistributed.
- On GitHub's public Ubuntu runner, publisher's Nature/Springer PDF endpoints returned `200 text/html` rather than binary PDFs; PMC also returned HTML and Europe PMC returned HTTP 403.
- **Verdict:** `BLOCKED_SOURCE_PDF_UNAVAILABLE`. The package installed successfully, but this probe **did not** reach `inspect_pdf`, `extract_regions` or rendering. No claims about Celina card quality.
- Evidence: [GitHub Actions run 42562587064](https://github.com/Lu18835713910/paper-figure-story-SharePack/actions/runs/42562587064).

## Probe B — scVI genuine preprint

- Lopez, Regier, Cole, Jordan & Yosef, *A deep generative model for gene expression profiles from single-cell RNA sequencing*, arXiv:1709.02082 (2017, v4 January 2018). **Not** the distinct typeset Nature Methods 2018 PDF.
- The runner successfully fetched `https://arxiv.org/pdf/1709.02082` and validated `%PDF-`.
- PDF SHA-256: `edfaece53e86fe4dde79528020d642de3b86f389dcd9a665f471f991c1ace3eb`.
- PDF pages: **6**.
- `inspect_pdf`: **2 Figure caption candidates** — Fig. 1 at page 2 and Fig. 2 at page 4. Both remain `CANDIDATE_NOT_PANEL_VERIFIED`.
- `extract_regions`: 2 PDF-coordinate crops, `review_status=PENDING`. They are provisional source candidates, **not verified panel-identical illustrations**.
- A manually structured **engineering test** story (not a final independent domain review) used these assets for an 8-card standard profile.
- `validate_story`: `valid=true` (structural only), `formal_ready=false`; warnings for both assets and eight claims `PENDING`.
- `render(layout_engine="freeform",render_png=False)`: **success**, **8 slides**, PPTX size **341,811 bytes**; layout modes = `logic`, `text_synthesis`, `figure_hero`, `figure_split`; no reported text-text box collisions, canvas overflow, or under-threshold figure slots.
- `release_ready=false`: blockers `SCIENCE_AND_WINDOWS_VISUAL_REVIEW_NOT_PERFORMED` and `PANEL_SELECTION_NOT_REVIEWED`.
- **No actual LibreOffice/PDF/PNG render and no desktop/mobile screenshot inspection in this probe.** Structural geometry is not proof of visual correctness.
- Evidence: [GitHub Actions run 42562873652](https://github.com/Lu18835713910/paper-figure-story-SharePack/actions/runs/42562873652), `scvi-preprint-probe` job.

## Important scientific coverage gap

The scVI source contains **four central tables (Tables 1–4)** showing held-out model fit, imputation, clustering and batch/unwanted-variation comparisons, alongside its two figures. A workflow that captures only `Fig.`/`Figure` captions can successfully generate a deck while omitting original **tables with critical evidence**. Therefore, a successful PDF scan or eight-page PPTX is **not a complete study explanation**.

Current `ingest.CAPTION` recognizes only captions that start a PDF text block in specific Figure formats; this is useful but brittle on multi-column papers, supplementary figures, tables, and alternate capitalization. Candidate rectangle selection from page top to caption top can include unrelated text or crop parts of panels; correct figure identity must be checked before promotion to reviewed.

## Prioritized improvement decisions

| Priority | Issue | Suggested acceptance criterion |
| --- | --- | --- |
| **P0** | Figure/Table discovery and panel integrity | Detect `Fig.` and `Table` candidates, map each to a source PDF page and element rectangle, and require human review for every exact crop. No automatic `VISUAL_REVIEWED`. |
| **P0** | Evidence coverage before story rendering | Require a per-paper inventory of all main Figures **and Tables**, including `USED/EXPLAINED/NOT_RELEVANT/NEEDS_REVIEW` disposition, with scientific rationale. A structural pass must not be treated as a complete research story. |
| **P1** | Reliable source PDF acquisition | Differentiate `HTTP 200 text/html`, CAPTCHAs/403, invalid PDF, missing supplement and true parser exceptions; offer manually supplied PDF as first-class offline route. |
| **P1** | Full page source binding | Each claim and metric should point to the actual Figure panel, Table row, or text passage and PDF page. Validate page bounds and reject undeclared/contradictory references. |
| **P1** | Cross-paper story / layout match | A 6-page methods article should use an appropriate concise story plan with tables, not fill a fixed number of cards by duplicating Figure assets or generic language. Keep recommended 8–10 as flexible rather than target-driven. |
| **P1** | Stronger visual QA | Export to true PowerPoint/LibreOffice-rendered PDF and 1080×1440 PNG, inspect all cards for clipping/font-substitution and 400px mobile readability; geometry-only QA is insufficient. |
| **P2** | Controlled regression corpus | Include at least three genuine papers with different layouts (method with tables, wet-lab with multi-panels, spatial-omics with tissue images), with SHA-pinned reference PDFs and reviewed ground-truth manifests. Avoid publishing restricted source PDFs. |
| **P2** | UX and trust labeling | Explain `candidate PDF index` ≠ `scientific review` ≠ `visually accepted card`, and separate renderer errors from source/access blockers. |

## Decision

- **scVI: ENGINEERING_PARTIAL_PASS** for true PDF acquisition, candidate Figure indexing, source crop, structural validation, and native editable PPTX creation.
- **Celina: INPUT_BLOCKED**; no inferences about scientific/story/visual quality.
- **Independent formal cross-paper science and mobile QA: NOT_DONE**.
- **Do not tag public Beta or merge this test branch automatically.** A separate correction candidate must pass story/source review, output rendering, and visual verification before product changes go to `main`.

Proposed next engineering batch: **Table coverage + exact Figure candidate review + robust document-source diagnostics**. Preserve working PFS bridge behavior and versioned science evidence.
