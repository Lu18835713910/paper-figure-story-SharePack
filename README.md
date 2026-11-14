# SharePack 1.0.0

SharePack renders Agent-edited research stories as editable portrait PowerPoint cards. Source registries bind figure regions to the paper PDF. Use PowerPoint PDF export and 400px previews for final visual review.

## Install and verify

Install the 1.0.0 wheel from the GitHub release.

```console
python -m pip install paper_figure_story_sharepack-1.0.0-py3-none-any.whl
python -m sharepack --help
```

To try the original fictional demonstration from this source tree:

```console
python scripts/render_reviewed.py --pdf examples/original_demo/sample.pdf --story examples/original_demo/story.json --plan examples/original_demo/plan.json --output out_original_demo
```

See [SKILL.md](SKILL.md) for the Agent workflow and source review.

## Scope and status

Standalone runs from reviewed editorial inputs. PFS integration consumes M1 and source-verified Figure assets. Source-bound research-logic projections use a separate explicit Research Logic model. A real-paper PFS v1.2.0 case completed the source-bound planning and editorial rendering workflow. Some original chart labels need the full-size PDF. WorkBuddy routing has not been verified.

Public examples use original fictional content. See [LICENSE_STATUS.md](LICENSE_STATUS.md) for software rights. Private paper figures and journal branding are outside the public distribution.

## PDF support

`python -m sharepack prepare --pdf PAPER --outdir INDEX` extracts page text and lists caption candidates. This index does not produce speculative crop thumbnails. Use reviewed region coordinates and `extract-reviewed-figures` to generate figures with auditable source identities. Region coordinates are relative to the displayed page, after CropBox and rotation.

XObject extraction is limited to directly displayed image objects. Nested object extraction and XObject display rectangles are outside this release scope. Use a reviewed rendered page region for nested content. Pages using non-default PDF UserUnit are rejected. Historical image-byte approvals can require review if the PDF engine produces a different encoding.
