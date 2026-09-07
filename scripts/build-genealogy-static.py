#!/usr/bin/env python3
"""Render the family tree as static HTML for JS-less readers.

The interactive explorer on /genealogy renders pedigree-data.json
client-side, which leaves the tree unreadable to AI crawlers and text
extractors (they see template placeholders, and many drop CSS-hidden or
collapsed content). This script renders the same public JSON into:

  1. family-tree.html — a standalone, fully static, always-visible page
     with every person (served at /family-tree).
  2. A short static paragraph on genealogy.html (between the
     genealogy-static markers) naming the direct Bell line and linking
     to the full text page.

Run from the repo root. Fetches the live JSON first so a deploy always
ships current data; falls back to the committed snapshot offline.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

LIVE_URL = "https://alexandertbell.com/pedigree/pedigree-data.json"
ROOT = Path(__file__).resolve().parent.parent
GENEALOGY = ROOT / "genealogy.html"
TREE_PAGE = ROOT / "family-tree.html"
SNAPSHOT = ROOT / "pedigree-data.json"
BEGIN = "<!-- genealogy-static:begin -->"
END = "<!-- genealogy-static:end -->"

GRADE_LABEL = {"ok": "Documented", "part": "Probable", "hyp": "Hypothesis"}

GOATCOUNTER = ('<script data-goatcounter="https://alexandertbell.goatcounter.com/count" '
               'async src="//gc.zgo.at/count.js"></script>')


def load_data():
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


def entry_html(n, p):
    name = p.get("n", "").strip()
    dates = p.get("d", "").strip()
    grade_line = p.get("gl", "") or GRADE_LABEL.get(p.get("g", ""), "")
    story = p.get("s", "") or ""
    evidence = p.get("x", "") or ""
    dates_span = f' <span class="dt">({dates})</span>' if dates else ""
    h = [f'<article id="p{n}">\n<h3>{name}{dates_span}</h3>',
         f'<p class="meta">Ahnentafel #{n} · {relationship(n)} · {grade_line}</p>']
    if story:
        h.append(story)
    if evidence:
        h.append(f'<p class="evhead">Evidence</p>{evidence}')
    h.append("</article>")
    return "\n".join(h)


def paternal_chain(data):
    chain, n = [], 1
    while str(n) in data:
        p = data[str(n)]
        d = p.get("d", "").strip()
        chain.append(f'{p["n"].strip()} ({d})' if d else p["n"].strip())
        n *= 2
    return chain


def build_tree_page(people, n_people):
    entries = "\n".join(entry_html(n, p) for n, p in people)
    desc = (f"The complete Bell family tree of Alexander (Alec) T. Bell as plain text: "
            f"{n_people} people with names, dates, relationships, stories, and evidence grades.")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Family tree · Alexander T. Bell</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="https://alexandertbell.com/family-tree">
<meta name="color-scheme" content="light dark">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="icon" type="image/x-icon" href="/favicon.ico" sizes="16x16 32x32 48x48">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:type" content="article">
<meta property="og:title" content="Family tree · Alexander T. Bell">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="https://alexandertbell.com/family-tree">
<meta property="og:site_name" content="Alexander T. Bell">
<meta property="og:image" content="https://alexandertbell.com/og-card.png?v=3">
{GOATCOUNTER}
<style>
  :root {{ --bg: #ffffff; --text: #17170f; --body-c: #4f4f4a; --faint: #a8a8a0; --divider: rgba(23, 23, 15, 0.12); --accent: #5c6534; --mark: #6b7346; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg: #23261b; --text: #edeee0; --body-c: #b4b5a3; --faint: #83866f; --divider: rgba(237, 238, 224, 0.14); --accent: #b9c08b; --mark: #8f9a55; }}
  }}
  body {{ margin: 0; background: var(--bg); color: var(--body-c); font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 14.5px; line-height: 1.62; }}
  .wrap {{ max-width: 760px; margin: 0 auto; padding: 56px 20px 72px; }}
  .dash {{ display: block; width: 18px; height: 3px; background: var(--mark); margin-bottom: 20px; }}
  h1 {{ font-size: 28px; font-weight: 700; letter-spacing: -0.03em; margin: 0 0 8px; color: var(--text); }}
  h3 {{ font-size: 16px; font-weight: 700; letter-spacing: -0.01em; margin: 34px 0 2px; color: var(--text); }}
  h3 .dt {{ font-weight: 400; color: var(--faint); }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; text-underline-offset: 4px; }}
  .meta {{ margin: 0 0 8px; font-size: 12px; color: var(--faint); }}
  .evhead {{ margin: 10px 0 0; font-size: 11.5px; color: var(--faint); font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; }}
  article {{ border-top: 1px solid var(--divider); padding-top: 4px; }}
  .intro p {{ margin: 0 0 10px; }}
  .foot {{ margin-top: 44px; padding-top: 18px; border-top: 1px solid var(--divider); font-size: 11.5px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--faint); display: flex; justify-content: space-between; }}
</style>
</head>
<body>
<div class="wrap">
  <span class="dash"></span>
  <h1>The family tree, in full<span style="color: var(--mark)">.</span></h1>
  <div class="intro">
    <p>The complete text of my genealogy research — the same data the <a href="/genealogy">interactive explorer</a> renders, written out so it can be read without JavaScript. {n_people} people, numbered by <a href="https://en.wikipedia.org/wiki/Ahnentafel">ahnentafel</a>: #1 is me, each person’s father is double their number, each mother is double plus one.</p>
    <p>Deeper reading: <a href="/pedigree/">the research view with photographs and scanned evidence</a>, <a href="/pedigree/bell-lineage">the Bell paternal line as a narrative</a>, <a href="/pedigree/bell-deep-line">the evidence map for the deep Bell line</a>. Machine-readable: <a href="/pedigree/pedigree-data.json">pedigree-data.json</a>.</p>
  </div>
{entries}
  <div class="foot"><span><a href="/" style="color: inherit">Alexander T. Bell</a></span><span><a href="/genealogy" style="color: inherit">Back to the explorer</a></span></div>
</div>
</body>
</html>
"""


def main():
    data = load_data()
    people = sorted(((int(k), v) for k, v in data.items()), key=lambda kv: kv[0])
    n_people = len(people)

    TREE_PAGE.write_text(build_tree_page(people, n_people))
    print(f"family-tree.html written ({TREE_PAGE.stat().st_size} bytes, {n_people} people)")

    chain = " → ".join(paternal_chain(data))
    block = (
        f'{BEGIN}\n'
        '<div id="genealogy-text" style="max-width: 760px; padding: 34px 20px 10px; font-size: 13.5px; line-height: 1.6; color: var(--body-c)">\n'
        f'<p style="margin: 0 0 8px">Every person on this chart is also published as plain text: <a href="/family-tree" style="font-weight: 700">the full family tree in text form</a> — all {n_people} people with dates, relationships, stories, and evidence grades. The direct Bell line runs {chain}.</p>\n'
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
