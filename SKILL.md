---
name: paper-figure-story-sharepack
description: Draft figure-grounded scientific story cards with source-linked evidence; PFS input optional.
---

# SharePack v0.1.0-rc.1 · Pre-release

SharePack is a source-grounded science communication workflow plus a Python CLI.
The CLI does **not** infer trustworthy scientific conclusions from an arbitrary PDF automatically.
An Agent or human reviewer must validate the paper, Figure panels, controls, numbers and limitations before preparing `story.json`.

## Standalone mode (no PFS required)
1. `sharepack prepare --pdf paper.pdf --outdir work/index`
2. Review paper, captions, methods, panels, negative results and supplements where available.
3. Author `story.json` and registered `regions.json` from actual evidence.
4. `sharepack extract-regions --pdf paper.pdf --regions work/regions.json --outdir work/assets`
5. `sharepack audit-plan --story work/story.json --assets work/assets/assets.json --outdir work/audit`
6. `sharepack validate --story work/story.json --assets work/assets/assets.json`
7. `sharepack render --story work/story.json --assets work/assets/assets.json --outdir work/render --layout-engine freeform --no-pdf`
8. Inspect resulting PPTX in actual PowerPoint; ensure evidence and layout are correct. PNG/PDF rendering may require LibreOffice.

## Optional PFS-assisted mode
When a validated PFS v1.1.1 M1 knowledge file exists, use `sharepack bridge-pfs --knowledge path/to/knowledge.json --outdir work/bridge`.
For a verified Figure manifest, use `--pfs-assets` and, when needed, `--pfs-crosswalk` for stable identity mapping.
Do not infer scientific causality from PFS relation order. The experimental `pfs_logic_projection` pathway consumes real `pfs-research-logic-1` outputs, not a guessed M1 relationship list.

## Scientific constraints
- 8–10 pages typical; full profile at most 15. Choose by research story, not Figure count.
- Preserve source Figure content, experiment definitions, controls, sample sizes and statistical notation.
- Treat every computed QA pass as engineering evidence only, not independent science certification.
- Do not silently omit facts or unknown source status; if Figure is too dense, plan a new view or leave review pending.
- Preserve read-only upstream PFS data.

Release status: **experimental RC, cross-paper and clean Windows installation not yet validated**.
Read [README](README.md), [LIMITATIONS](docs/KNOWN_LIMITATIONS.md) and [NOTICE](NOTICE_THIRD_PARTY.md).
