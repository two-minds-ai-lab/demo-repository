<p align="center">
  <img src="assets/banner.svg" alt="Two Minds AI Lab — two minds, learning in public." width="100%">
</p>

<p align="center">
  <a href="https://github.com/two-minds-ai-lab/demo-repository/actions/workflows/proof-html.yml"><img src="https://github.com/two-minds-ai-lab/demo-repository/actions/workflows/proof-html.yml/badge.svg" alt="Proof HTML"></a>
  <img src="https://img.shields.io/badge/license-MIT-0e1118" alt="MIT licensed">
</p>

# Two Minds AI Lab

One person and one model, working things out together. What we learn goes here as we learn
it — the working-out included, not only the parts that came out clean.

Almost everything written about working with AI arrives as a finished result with the
learning taken out. The result is the least useful part of it. So we keep the rest, and we
publish it as we go.

**→ [two-minds-ai-lab.github.io/demo-repository](https://two-minds-ai-lab.github.io/demo-repository/)**

## Three rules

**Show the working-out.** The notes, the dead ends, and the version that did not work,
alongside whatever finally did.

**Claim nothing unshipped.** Nothing here describes work that does not exist yet. That is
why this repository is small.

**Correct it in the open.** When we get something wrong, the correction lands here too, and
the history keeps both.

## What's here

| Path | What it is |
| --- | --- |
| `index.html` | The whole site — markup, styles, and behaviour in one file |
| `assets/banner.svg` | The banner above |
| `.github/workflows/` | Checks the rendered HTML, and assigns an owner to new issues |
| `docs/superpowers/specs/` | The design spec the site was built from |

## Run it

No build step, no dependencies. Any static server works:

```bash
git clone https://github.com/two-minds-ai-lab/demo-repository.git
cd demo-repository
python3 -m http.server 8000
```

Then open <http://localhost:8000>.

## Notes on the build

Kept here because they are part of the working-out.

**One file.** GitHub Pages serves these files as they are, so `index.html` inlines its own
styles and script and makes zero external requests. A bundler or a CDN would not survive
the trip.

**System typefaces only.** No webfonts means no network round-trip and no layout shift.

**The seam.** The hero is typeset twice, once light and once dark, and the dark copy is
clipped at a divider that follows your pointer — so the headline inverts where the two
minds meet. Both copies carry the full text, so nothing is hidden when the script does not
run, and the duplicate is held back from assistive technology to avoid a doubled reading.

**What degrades.** Scroll reveals are gated behind a `.js` class, so no text is invisible
without JavaScript. `prefers-reduced-motion` pins the seam and drops every transition.
Below 860px the split turns on its side.

## License

[MIT](LICENSE) © Two Minds AI Lab
