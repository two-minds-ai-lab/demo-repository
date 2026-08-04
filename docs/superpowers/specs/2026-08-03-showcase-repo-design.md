# Two Minds AI Lab — Showcase Repository Design

Date: 2026-08-03
Status: Approved

## Goal

Convert `two-minds-ai-lab/demo-repository` from GitHub's stock demo repo into the
organization's official showcase: a distinctive landing page, a premium README, and an
organization profile page.

## Positioning

Two Minds AI Lab is one person and one model learning together, in public. The site exists
to state that vision and to show only what actually exists. All copy derives from that
positioning. No placeholder text ships, and nothing describes work that has not shipped.

Superseded (2026-08-03): an earlier pass positioned the lab around adversarial multi-agent
deliberation, with an invented research agenda and an illustrative debate transcript. That
claimed an agenda the lab had not earned, and it was cut. Kept here because the site's own
first rule is to show the working-out.

## Visual Direction — "A working document"

The page is a sheet with a real margin. One rule runs its whole length; the text sits to
the right of it and annotations hang to the left, the way notes get added to a page after
it was written. Two hands annotate — a person and a model — each with its own colour.

The signature is that the drafts stay on the page: what the site used to say is struck
through rather than deleted, with the reason kept beside it. These are the site's real
revisions. It is rule 01 applied to the page itself.

Superseded (2026-08-03): the first visual direction was a split light/dark poster with a
pointer-tracked seam through the hero. It failed on its own terms — the device was
announced in the hero and then absent from the rest of the page, and a static monument
contradicts a subject that is iterative and accumulating. The document direction carries
the same duality structurally rather than as an effect.

## Components

### 1. `index.html` — landing page

Constraint: GitHub Pages serves raw files with no build step, so the page must be fully
self-contained. Inline `<style>`, no script at all, zero external network requests. The
`@primer/css` dependency is not resolvable at runtime and has been removed.

Constraint: the existing `proof-html` workflow lints the page. Output must be valid,
semantic HTML.

Sections, in order:

1. Masthead — date in the margin, lab name and navigation on the sheet.
2. Title — the vision in one line, with the first annotation beside it.
3. Vision — why the working-out is the part worth keeping.
4. The drafts — what the page used to say, struck through, with the reason kept.
5. Three rules — what the vision commits the lab to. Promises, not results.
6. What is here — the repositories that actually exist. Nothing else goes in this list.
7. Footer — links and license.

Margin mechanic: every block on the sheet uses the same two columns, so the margin reads
as one continuous column. The rule is painted on the sheet itself rather than per-section,
so it never breaks between blocks. Below 900px the margin cannot hold a column, so
annotations drop in beneath what they annotate and move their coloured edge to the left.

No script. An earlier version needed one for a pointer-tracked hero effect. A document
does not, so the page ships with zero JavaScript.

Accessibility:
- Body and annotation text contrast-checked to WCAG AA on the sheet.
- Visible keyboard focus states.
- Semantic landmarks; the margin is a layout column, not a reading-order change.
- Struck-through drafts use real `line-through` text decoration, so the revision is
  conveyed to assistive technology and not by colour alone.

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
