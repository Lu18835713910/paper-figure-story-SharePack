# Known limitations / Release gates

Status of `v0.1.0-rc.1` (as of 2026-11-07):

| Area | Current evidence | Release gate |
|---|---|---|
| Structural code tests | 44 passing in isolated Python test environment for dev.5 core | Cannot substitute for science/visual QA |
| Source-pinned PFS model bridge | Validated on Passmore case in prior WorkBuddy testing | Cross-paper PFS regression still required |
| Actual ten-page case study | Created from curated scientific story and existing verified Figure assets | Not a one-command automatic generative workflow |
| Image/text editing | Native editable PPTX text/shapes; original panels embedded | Final visual review depends on Office/fonts |
| Visual scale | Dense two-figure pages can require zoom on mobile | Test multiple phone screen sizes |
| Scientific claims | Main article captions/Results checked on one paper; some supplements unavailable | Independent full science review pending |
| Clean setup | Python package builds, but not an untouched user Windows host | Clean-install smoke test pending |
| Other journals/papers | One complete case study | Independent cross-paper E2E test pending |
| Code/license | Copyright holder license not selected | License choice and rights policy pending |

**What the 10-card demo does NOT establish**: that the SharePack CLI automatically authored and scientifically validated all text from a brand-new PDF, that its latest bespoke visual design is entirely present in general-purpose dev.5 rendering, or that PFS improves blind performance by a measured percentage.

Do not ship a public beta label before closing the outstanding installation, cross-paper, scientific, and license gates.
