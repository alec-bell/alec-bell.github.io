#!/usr/bin/env python3
"""Render the family tree as static HTML for JS-less readers.

The interactive explorer on /genealogy renders pedigree-data.json
client-side, which leaves the tree unreadable to AI crawlers and text
extractors (they see template placeholders, and many drop CSS-hidden or
collapsed content). This script renders the same public JSON into:

  1. family-tree.html — the complete tree on one standalone static page
     (served at /family-tree): every person with dates, relationship,
     evidence grade, story, evidence notes, and the text of every photo
     and evidence-scan caption.
  2. family-tree-<n>.html — the same entries split into parts of roughly
     PART_BUDGET bytes each, for readers that truncate large pages. Parts
     canonicalize to /family-tree so search engines index only the full page.
  3. A short static paragraph on genealogy.html (between the
     genealogy-static markers) naming the direct Bell line and linking
     to the full text page.

Run from the repo root. Data comes from, in order of preference:

  1. $PEDIGREE_DATA_FILE — a locally built pedigree-data.json. This is what
     the genealogy repo's _tools/deploy_all.sh passes in, so the family-tree
     pages are built from the same data as the chart in the same run,
     without waiting for GitHub Pages to redeploy the pedigree site first.
  2. the live JSON at alexandertbell.com/pedigree/.
  3. the committed snapshot, when offline.
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

LIVE_URL = "https://alexandertbell.com/pedigree/pedigree-data.json"
ROOT = Path(__file__).resolve().parent.parent
GENEALOGY = ROOT / "genealogy.html"
SNAPSHOT = ROOT / "pedigree-data.json"
BEGIN = "<!-- genealogy-static:begin -->"
END = "<!-- genealogy-static:end -->"
PART_BUDGET = 100_000  # bytes of entry HTML per part page

GRADE_LABEL = {"ok": "Documented", "part": "Probable", "hyp": "Hypothesis"}
FLAG_LABEL = {"patriot": "Revolutionary patriot", "immigrant": "Immigrant"}

GOATCOUNTER = ('<script data-goatcounter="https://alexandertbell.goatcounter.com/count" '
               'async src="//gc.zgo.at/count.js"></script>')


def load_data():
    local = os.environ.get("PEDIGREE_DATA_FILE")
    if local:
        raw = Path(local).read_text(encoding="utf-8")
        SNAPSHOT.write_text(raw)
        print(f"using local JSON {local} ({len(raw)} bytes), snapshot updated")
        return json.loads(raw)
    try:
        with urllib.request.urlopen(LIVE_URL, timeout=30) as r:
            raw = r.read().decode()
        SNAPSHOT.write_text(raw)
        print(f"fetched live JSON ({len(raw)} bytes), snapshot updated")
        return json.loads(raw)
    except Exception as e:
        print(f"live fetch failed ({e}); using committed snapshot")
        return json.loads(SNAPSHOT.read_text())


def relationship(n):
    if n == 1:
        return "the starting point of the chart"
    bits = bin(n)[3:]
    words = ["father" if b == "0" else "mother" for b in bits]
    path = "’s ".join(words)
    gens = len(bits)
    gen_note = "1 generation back" if gens == 1 else f"{gens} generations back"
    return f"his {path} ({gen_note})"


def media_list(items, label):
    if not items:
        return ""
    figs = []
    for it in items:
        u = (it.get("u") or "").strip()
        cap = (it.get("c") or "").strip()
        why = (it.get("w") or "").strip()
        caption = f"<b>{cap}</b>" if cap else ""
        if why:
            caption += f" — {why}" if caption else why
        img = f'<img src="/pedigree/{u}" alt="{cap}" loading="lazy" decoding="async">' if u else ""
        if img or caption:
            figs.append(f"<figure>{img}<figcaption>{caption}</figcaption></figure>")
    if not figs:
        return ""
    return f'<p class="evhead">{label}</p>' + "\n".join(figs)


def fetch_orphan_images(referenced):
    """Images in the pedigree repo's img/ that no JSON entry references —
    continuation pages of multi-page scans. Listed in an appendix so every
    published image is reachable from static HTML. Best-effort: skipped if
    the GitHub API is unavailable."""
    try:
        with urllib.request.urlopen(
                "https://api.github.com/repos/alec-bell/pedigree/contents/img", timeout=30) as r:
            listing = json.load(r)
        files = {e["name"] for e in listing if e.get("type") == "file"}
        return sorted(files - {u.replace("img/", "") for u in referenced})
    except Exception as e:
        print(f"orphan-image listing skipped ({e})")
        return []


def update_sitemap(refs, orphans):
    """Maintain the image-sitemap entries for /family-tree between markers."""
    sm = ROOT / "sitemap.xml"
    s = sm.read_text()
    b, e = "<!-- family-tree-images:begin -->", "<!-- family-tree-images:end -->"
    if b not in s or e not in s:
        print("sitemap image markers missing, skipped")
        return
    urls = [f"https://alexandertbell.com/pedigree/{u}" for u in dict.fromkeys(refs)]
    urls += [f"https://alexandertbell.com/pedigree/img/{n}" for n in orphans]
    body = "\n".join(f"    <image:image><image:loc>{u}</image:loc></image:image>" for u in urls)
    s = s[:s.index(b) + len(b)] + "\n" + body + "\n    " + s[s.index(e):]
    sm.write_text(s)
    print(f"sitemap: {len(urls)} family-tree image entries")


def orphan_appendix(orphans):
    if not orphans:
        return ""
    figs = []
    for name in orphans:
        cap = re.sub(r"\.[a-z]+$", "", name).strip("-").replace("-", " ")
        figs.append(f'<figure><img src="/pedigree/img/{name}" alt="{cap}" loading="lazy" decoding="async">'
                    f"<figcaption>{cap}</figcaption></figure>")
    return ('<article id="record-pages">\n<h3>Additional record pages</h3>\n'
            '<p class="meta">Continuation pages of multi-page evidence scans above — every published '
            'scan, reachable in full. Captions are derived from the archival filenames.</p>\n'
            + "\n".join(figs) + "\n</article>")


def entry_html(n, p):
    name = p.get("n", "").strip()
    dates = p.get("d", "").strip()
    grade_line = p.get("gl", "") or GRADE_LABEL.get(p.get("g", ""), "")
    flags = " · ".join(FLAG_LABEL.get(f, f) for f in p.get("fl", []) or [])
    story = p.get("s", "") or ""
    evidence = p.get("x", "") or ""
    dates_span = f' <span class="dt">({dates})</span>' if dates else ""
    meta = f"Ahnentafel #{n} · {relationship(n)} · {grade_line}"
    if flags:
        meta += f" · {flags}"
    h = [f'<article id="p{n}">\n<h3>{name}{dates_span}</h3>',
         f'<p class="meta">{meta}</p>']
    if story:
        h.append(story)
    if evidence:
        h.append(f'<p class="evhead">Evidence</p>{evidence}')
    h.append(media_list(p.get("ph"), "Photographs (described)"))
    h.append(media_list(p.get("ev"), "Evidence images (described)"))
    h.append("</article>")
    return "\n".join(x for x in h if x)


def paternal_chain(data):
    chain, n = [], 1
    while str(n) in data:
        p = data[str(n)]
        d = p.get("d", "").strip()
        chain.append(f'{p["n"].strip()} ({d})' if d else p["n"].strip())
        n *= 2
    return chain


STYLE = """<style>
  :root { --bg: #ffffff; --text: #17170f; --body-c: #4f4f4a; --faint: #a8a8a0; --divider: rgba(23, 23, 15, 0.12); --accent: #5c6534; --mark: #6b7346; }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #23261b; --text: #edeee0; --body-c: #b4b5a3; --faint: #83866f; --divider: rgba(237, 238, 224, 0.14); --accent: #b9c08b; --mark: #8f9a55; }
  }
  body { margin: 0; background: var(--bg); color: var(--body-c); font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 14.5px; line-height: 1.62; }
  .wrap { max-width: 760px; margin: 0 auto; padding: 56px 20px 72px; }
  .dash { display: block; width: 18px; height: 3px; background: var(--mark); margin-bottom: 20px; }
  h1 { font-size: 28px; font-weight: 700; letter-spacing: -0.03em; margin: 0 0 8px; color: var(--text); }
  h3 { font-size: 16px; font-weight: 700; letter-spacing: -0.01em; margin: 34px 0 2px; color: var(--text); }
  h3 .dt { font-weight: 400; color: var(--faint); }
  a { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; text-underline-offset: 4px; }
  .meta { margin: 0 0 8px; font-size: 12px; color: var(--faint); }
  .evhead { margin: 10px 0 0; font-size: 11.5px; color: var(--faint); font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; }
  figure { margin: 10px 0 0; }
  figure img { display: block; max-width: min(420px, 100%); height: auto; border: 1px solid var(--divider); }
  figcaption { font-size: 12.5px; margin-top: 4px; max-width: 640px; }
  figcaption b { color: var(--text); font-weight: 700; }
  article { border-top: 1px solid var(--divider); padding-top: 4px; }
  .intro p { margin: 0 0 10px; }
  .foot { margin-top: 44px; padding-top: 18px; border-top: 1px solid var(--divider); font-size: 11.5px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--faint); display: flex; justify-content: space-between; }
</style>"""


def page_shell(title, desc, canonical_path, h1, intro_html, entries_html):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="https://alexandertbell.com{canonical_path}">
<meta name="color-scheme" content="light dark">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="icon" type="image/x-icon" href="/favicon.ico" sizes="16x16 32x32 48x48">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="https://alexandertbell.com{canonical_path}">
<meta property="og:site_name" content="Alexander T. Bell">
<meta property="og:image" content="https://alexandertbell.com/og-card.png?v=3">
{GOATCOUNTER}
{STYLE}
</head>
<body>
<div class="wrap">
  <span class="dash"></span>
  <h1>{h1}<span style="color: var(--mark)">.</span></h1>
  <div class="intro">
{intro_html}
  </div>
{entries_html}
  <div class="foot"><span><a href="/" style="color: inherit">Alexander T. Bell</a></span><span><a href="/genealogy" style="color: inherit">Back to the explorer</a></span></div>
</div>
</body>
</html>
"""


def split_parts(rendered):
    """rendered: list of (n, html). Returns list of lists, ~PART_BUDGET bytes each."""
    parts, cur, size = [], [], 0
    for n, html in rendered:
        if cur and size + len(html) > PART_BUDGET:
            parts.append(cur)
            cur, size = [], 0
        cur.append((n, html))
        size += len(html)
    if cur:
        parts.append(cur)
    return parts


def main():
    data = load_data()
    people = sorted(((int(k), v) for k, v in data.items()), key=lambda kv: kv[0])
    n_people = len(people)
    rendered = [(n, entry_html(n, p)) for n, p in people]
    parts = split_parts(rendered)
    refs = [it["u"] for _, p in people for lst in (p.get("ph") or [], p.get("ev") or [])
            for it in lst if it.get("u")]
    orphans = fetch_orphan_images(refs)
    appendix = orphan_appendix(orphans)
    update_sitemap(refs, orphans)

    def part_links():
        return ", ".join(
            f'<a href="/family-tree-{i + 1}">part {i + 1} (#{chunk[0][0]}–#{chunk[-1][0]})</a>'
            for i, chunk in enumerate(parts))

    common_intro = (
        f'<p>{n_people} people, numbered by <a href="https://en.wikipedia.org/wiki/Ahnentafel">ahnentafel</a>: '
        '#1 is me, each person’s father is double their number, each mother is double plus one. '
        'Every entry carries its dates, relationship, evidence grade, story, evidence notes, and text '
        'descriptions of every photograph and evidence scan.</p>'
        '<p>Deeper reading: <a href="/pedigree/">the research view with photographs and scanned evidence</a>, '
        '<a href="/pedigree/bell-lineage">the Bell paternal line as a narrative</a>, '
        '<a href="/pedigree/bell-deep-line">the evidence map for the deep Bell line</a>. '
        'Machine-readable: <a href="/pedigree/pedigree-data.json">pedigree-data.json</a>.</p>'
    )

    # Full page.
    full_intro = (
        '<p>The complete text of my genealogy research — the same data the '
        '<a href="/genealogy">interactive explorer</a> renders, written out so it can be read without JavaScript.</p>'
        + common_intro +
        f'<p>This page is long. If your reader truncates large pages, the same entries are split into '
        f'smaller sections: {part_links()}.</p>'
    )
    desc = (f"The complete Bell family tree of Alexander (Alec) T. Bell as plain text: "
            f"{n_people} people with names, dates, relationships, stories, and evidence.")
    (ROOT / "family-tree.html").write_text(page_shell(
        "Family tree · Alexander T. Bell", desc, "/family-tree",
        "The family tree, in full", full_intro,
        "\n".join(h for _, h in rendered) + "\n" + appendix))

    # Part pages (canonicalize to the full page).
    for i, chunk in enumerate(parts):
        lo, hi = chunk[0][0], chunk[-1][0]
        intro = (
            f'<p>Part {i + 1} of {len(parts)} of <a href="/family-tree">the full family tree in text form</a>, '
            f'covering ahnentafel #{lo}–#{hi}. All parts: {part_links()}.</p>' + common_intro)
        (ROOT / f"family-tree-{i + 1}.html").write_text(page_shell(
            f"Family tree, part {i + 1} · Alexander T. Bell",
            f"Part {i + 1} of the Bell family tree in text form: ahnentafel #{lo}–#{hi}.",
            "/family-tree",  # canonical: the full page
            f"The family tree, part {i + 1}", intro,
            "\n".join(h for _, h in chunk) + ("\n" + appendix if i == len(parts) - 1 else "")))

    # Remove stale part files beyond the current count.
    for stale in ROOT.glob("family-tree-*.html"):
        m = re.match(r"family-tree-(\d+)\.html$", stale.name)
        if m and int(m.group(1)) > len(parts):
            stale.unlink()
            print(f"removed stale {stale.name}")

    total = sum(len(h) for _, h in rendered)
    print(f"family-tree.html + {len(parts)} parts written ({n_people} people, {total} bytes of entries)")

    # Compact block on /genealogy.
    chain = " → ".join(paternal_chain(data))
    block = (
        f'{BEGIN}\n'
        '<div id="genealogy-text" style="max-width: 760px; padding: 34px 20px 10px; font-size: 13.5px; line-height: 1.6; color: var(--body-c)">\n'
        f'<p style="margin: 0 0 8px">Every person on this chart is also published as plain text: <a href="/family-tree" style="font-weight: 700">the full family tree in text form</a> — all {n_people} people with dates, relationships, stories, and evidence grades (also in smaller sections: {part_links()}). The direct Bell line runs {chain}.</p>\n'
        '<p style="margin: 0">Also static: <a href="/pedigree/bell-lineage">the Bell paternal line as a narrative</a> and <a href="/pedigree/bell-deep-line">the evidence map</a>. Machine-readable: <a href="/pedigree/pedigree-data.json">pedigree-data.json</a>.</p>\n'
        '</div>\n'
        f'{END}'
    )
    page = GENEALOGY.read_text()
    pattern = re.escape(BEGIN) + r".*?" + re.escape(END)
    if not re.search(pattern, page, re.S):
        sys.exit("genealogy-static markers not found in genealogy.html")
    GENEALOGY.write_text(re.sub(pattern, lambda _: block, page, flags=re.S))
    print("genealogy.html block updated")


if __name__ == "__main__":
    main()
