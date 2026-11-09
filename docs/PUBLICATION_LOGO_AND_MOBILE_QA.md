# Publication style & publisher-logo integration — controlled QA

Status: **ISOLATED CANDIDATE, NOT MERGED OR RELEASED** (2026-11-09).

## Behavior

SharePack chooses publication style from the actual uploaded document edition and its source-bound metadata. It may show the *unaltered, genuine journal logo* in the masthead **only when the applicable display rights are documented**. An OA paper's CC BY license is **not** itself permission to use the journal's brand logo.

When no authorized mark exists, the card shows the journal name and a SharePack editorial masthead. No AI-created approximation of an official journal logo is used. The footer retains the independent-project notice.

### CLI

```powershell
sharepack render --story work/story.json --assets work/assets/assets.json --pdf-index work/index/pdf_index.json --logo-manifest work/logo/license_manifest.json --outdir work/output
```

`--logo-manifest` is optional. The command refuses unknown rights or a logo whose journal/style/DOI/source edition/hash do not match. Manifest example (replace all placeholder values with *documented* facts):

```json
{
  "contract": "sharepack-journal-logo-v1",
  "style_id": "journal-plos-computational-biology",
  "source_type": "journal",
  "doi": "10.1371/journal.pcbi.EXAMPLE",
  "publisher_name": "PLOS",
  "source_url": "https://OFFICIAL-SOURCE/UNCHANGED-LOGO.png",
  "permission_evidence_url": "https://WRITTEN-PERMISSION-EVIDENCE",
  "rights_basis": "written_permission",
  "original_sha256": "SHA256_OF_EXACT_PNG_BYTES",
  "file": "authorized_logo.png"
}
```

No logo file or fictional permission document is bundled.

**Policy sources:** [PLOS API display policy](https://api.plos.org/api-display-policy/) (no brand modifications or misleading association), [PLOS press guidelines](https://plos.org/media/guideline/). Logo rights and Article Figure licenses are separate.

## Test evidence

- Four Python versions (3.10–3.13), including a synthetic non-publisher fixture; verifies logo becomes an editable PPTX image object, SHA binding, DOI/style/edition checks and fail-closed on missing rights. The synthetic image is **not** displayed as a real journal logo in public samples.
- Genuine preprint PDF: scVI (arXiv:1709.02082), `preprint-arxiv`, PPTX+8 PNG, scientific review `PENDING`.
- Genuine journal PDF: *PLOS Computational Biology* (DOI 10.1371/journal.pcbi.1012818), `journal-plos-computational-biology`, PPTX+8 PNG, scientific review `PENDING`.
- Result without documented permission: `publication_logo.status=NOT_EMBEDDED_NO_VERIFIED_PERMISSION`; **no real logo embedded** in the public real-paper QA outputs.
- Changed no genuine publisher art. Do not represent the synthetic unit-test mark as PLOS branding or a marketing sample.
- Replaced the repetitive flowchart on `synthesis`/`limits` pages with larger editorial question–method–observation–takeaway–limits text blocks, retaining all core evidence. Non-figure workflow pages in other roles still need attention.
- Mobile QA records warnings when estimated text size is smaller than 12px at 400px display width.

## Still blocked

1. Obtain a journal logo with clear, applicable display permission; record official source and unchanged PNG bytes, then run real-license e2e.
2. Scientific Figure and Table exact cropping is not yet independently verified; candidate regions may include surrounding paragraphs.
3. Mobile-size labels/legends remain too small in several cards; extensive actual phone reading and Windows Office rendering are not complete.
4. The visual style is a restrained editorial interpretation, **not** a faithful journal cover, official journal product, or endorsement.
5. Avoid merging into main or releasing Beta before these are closed.
