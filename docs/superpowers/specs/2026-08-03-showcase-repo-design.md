# Two Minds AI Lab — Showcase Repository Design

Date: 2026-08-03
Status: Approved

## Goal

Convert `two-minds-ai-lab/demo-repository` from GitHub's stock demo repo into the
organization's official showcase: a distinctive landing page, a premium README, and an
organization profile page.

## Positioning

Two Minds AI Lab is an AI research lab focused on multi-agent systems and human+AI
collaboration. All copy derives from that positioning. No placeholder text ships.

## Visual Direction — "Two Minds"

The page is split: a light half (human intent) and a dark half (machine reason), meeting
at a seam running down the viewport. Content crossing the seam inverts. The seam is
structural — it organizes real content — not decoration.

Fallback: if the split direction does not earn itself on first render, fall back to a
dark technical/terminal-lab direction. This is a judgment call made at review time.

## Components

### 1. `index.html` — landing page

Constraint: GitHub Pages serves raw files with no build step, so the page must be fully
self-contained. Inline `<style>`, inline `<script>`, zero external network requests. The
`@primer/css` dependency is not resolvable at runtime and is not used.

Constraint: the existing `proof-html` workflow lints the page. Output must be valid,
semantic HTML.

Sections, in order:

1. Split hero — thesis statement, lab name, primary nav.
2. Capability triptych — research / tooling / open source.
3. Convergence panel — one prompt resolved by two agents whose outputs converge.
4. Artifacts strip — repository/output index.
5. Footer — contact and links.

Seam mechanic: two stacked layers, the upper one inset via `clip-path`. Divider position
is driven by pointer X on desktop with a scroll-linked default. Under 768px the layout
stacks vertically and the seam becomes a horizontal rule between stacked halves.

Accessibility:
- Both halves independently contrast-checked (WCAG AA minimum for body text).
- `prefers-reduced-motion: reduce` pins the seam at 50% and removes transitions.
- Visible keyboard focus states on both halves.
- Semantic landmarks; the split is presentational and does not affect reading order.

### 2. `README.md`

Replaces the stock GitHub demo copy entirely. Contains:
- Committed SVG banner in `assets/`.
- Badge row (existing two workflow badges).
- One-line positioning statement.
- What's inside (table).
- Local-run quickstart.
- Repository structure map.
- Contributing pointer and license.

### 3. Organization profile

New public repository `two-minds-ai-lab/.github` containing `profile/README.md`. This is
what renders at github.com/two-minds-ai-lab. Contains lab intro, focus areas, repository
index, and contact.

## GitHub Operations

- `demo-repository` visibility: private -> public (required for Pages on the Free plan).
- GitHub Pages: enabled on `main`, root directory.
- Both existing workflows (`auto-assign`, `proof-html`) must remain green.
- Org description and website URL require `admin:org` scope, which the current token
  lacks (`read:org` only). Deliver the re-auth command to the user rather than failing
  silently.

## Out of Scope

CONTRIBUTING.md, SECURITY.md, CODE_OF_CONDUCT.md, CODEOWNERS, and issue/PR templates.
The chosen scope is landing page plus README, not a full repository template. These can
be added later as a separate change.

## Success Criteria

- `index.html` renders the split design correctly in light and dark, desktop and mobile.
- `proof-html` workflow passes.
- README renders correctly on GitHub with a working banner.
- Org profile page shows custom content at github.com/two-minds-ai-lab.
- Pages URL serves the landing page.
