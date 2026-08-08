<p align="center">
  <img src="assets/banner.svg" alt="Two Minds AI Lab — two minds, learning in public." width="100%">
</p>

<p align="center">
  <a href="https://github.com/two-minds-ai-lab/demo-repository/actions/workflows/proof-html.yml"><img src="https://github.com/two-minds-ai-lab/demo-repository/actions/workflows/proof-html.yml/badge.svg" alt="Proof HTML"></a>
  <img src="https://img.shields.io/badge/license-MIT-191c18" alt="MIT licensed">
  <img src="https://img.shields.io/badge/javascript-none-a4560c" alt="No JavaScript">
</p>

# Two Minds AI Lab

One person and one model, working things out together. What we learn goes here as we learn
it — the working-out included, not only the parts that came out clean.

Almost everything written about working with AI arrives as a finished result with the
learning taken out. The result is the least useful part of it. So we keep the rest, and we
publish it as we go.

**→ [two-minds-ai-lab.github.io/demo-repository](https://two-minds-ai-lab.github.io/demo-repository/)**

## Three rules

**Show the working-out.** The notes, the dead ends, and the draft that did not work,
alongside whatever finally did.

**Claim nothing unshipped.** Nothing here describes work that does not exist yet. That is
why this repository is small.

**Correct it in the open.** When we get something wrong, the correction lands here too, and
the history keeps both.

## What's here

| Path | What it is |
| --- | --- |
| `index.html` | The whole page — markup and styles in one file, no script |
| `assets/banner.svg` | The banner above |
| `bill_analysis.py` | Deterministic recurring-bill analysis and report formatting |
| `data/bills.json` | Six-bill sample dataset with current and previous statements |
| `tests/` | Baseline pytest coverage for the bill analysis |
| `.github/workflows/` | Checks the rendered HTML, and assigns an owner to new issues |
| `docs/superpowers/specs/` | The design spec, including the direction that was abandoned |

## Run it

No build step, no dependencies. Any static server works:

```bash
git clone https://github.com/two-minds-ai-lab/demo-repository.git
cd demo-repository
python3 -m http.server 8000
```

Then open <http://localhost:8000>.

## Run the bill analysis

The Stage 0 bill analyzer uses only Python's standard library:

```bash
python bill_analysis.py
```

Run its tests with:

```bash
python -m pytest
```

## Notes on the build

Kept here because they are part of the working-out.

**The page is a sheet with a margin.** One rule runs its whole length. The text sits to the
right of it and the annotations hang to the left, the way notes get added to a page after
it was written. Two hands annotate — a person and a model — and each keeps its own colour.

**The drafts stay on the page.** What the site used to say is struck through rather than
deleted, with the reason kept beside it. Those are this page's real revisions, not
illustrations of the idea. It is the first rule applied to the page itself.

**No JavaScript.** An earlier version needed a script for a pointer-tracked effect in the
hero. A document does not need one, so there isn't one.

**One file, no build step.** GitHub Pages serves these files as they are, so `index.html`
inlines its own styles and makes zero external requests. A bundler or a CDN would not
survive the trip.

**System typefaces only.** A serif for reading and a monospace for the margin. No webfonts
means no network round-trip and no layout shift.

**What degrades.** Below 900px the margin cannot hold a column, so annotations drop in
beneath what they annotate and keep their coloured edge on the left.

## License

[MIT](LICENSE) © Two Minds AI Lab
