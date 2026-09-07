#!/usr/bin/env python3
"""Regenerate the static text version of the family tree inside genealogy.html.

The interactive explorer renders pedigree-data.json client-side, which leaves
the page unreadable to non-JS fetchers (AI crawlers, text extractors). This
script renders the same public JSON into semantic HTML between the
genealogy-static markers so the content is present in the served HTML.

Run from the repo root. Fetches the live JSON first so a deploy always ships
current data; falls back to the committed snapshot offline.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

LIVE_URL = "https://alexandertbell.com/pedigree/pedigree-data.json"
ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "genealogy.html"
SNAPSHOT = ROOT / "pedigree-data.json"
BEGIN = "<!-- genealogy-static:begin -->"
END = "<!-- genealogy-static:end -->"

GRADE_LABEL = {"ok": "Documented", "part": "Probable", "hyp": "Hypothesis"}


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
    grade = GRADE_LABEL.get(p.get("g", ""), "")
    grade_line = p.get("gl", "") or grade
    story = p.get("s", "") or ""
    evidence = p.get("x", "") or ""
    h = [f'<article>\n<h3 style="font-size: 15px; font-weight: 700; margin: 26px 0 2px">{name}'
         f'{" <span style=" + chr(34) + "font-weight: 400; color: var(--faint)" + chr(34) + ">(" + dates + ")</span>" if dates else ""}</h3>']
    h.append(f'<p style="margin: 0 0 8px; font-size: 12px; color: var(--faint)">Ahnentafel #{n} · {relationship(n)} · {grade_line}</p>')
    if story:
        h.append(story)
    if evidence:
        h.append(f'<p style="margin: 8px 0 0; font-size: 12.5px; color: var(--faint); font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase">Evidence</p>{evidence}')
    h.append("</article>")
    return "\n".join(h)


def main():
    data = load_data()
    people = sorted(((int(k), v) for k, v in data.items()), key=lambda kv: kv[0])
    n_people = len(people)

    intro = (
        '<p style="margin: 0 0 6px">This is the complete text of the family tree — the same data the '
        'interactive explorer above renders, written out so it can be read (and indexed) without JavaScript. '
        f'{n_people} people, numbered by <a href="https://en.wikipedia.org/wiki/Ahnentafel">ahnentafel</a>: '
        '#1 is Alexander Timothy Bell, each person’s father is double their number, each mother is double plus one.</p>'
        '<p style="margin: 0 0 6px">Deeper reading: <a href="/pedigree/">the research view with photographs and scanned evidence</a>, '
        '<a href="/pedigree/bell-lineage">the Bell paternal line as a narrative</a>, '
        '<a href="/pedigree/bell-deep-line">the evidence map for the deep Bell line</a>. '
        'Machine-readable: <a href="/pedigree/pedigree-data.json">pedigree-data.json</a>.</p>'
    )

    body = "\n".join(entry_html(n, p) for n, p in people)
    block = (
        f'{BEGIN}\n'
        '<div id="genealogy-text" style="max-width: 760px; padding: 40px 20px 24px; font-size: 13.5px; line-height: 1.6; color: var(--body-c)">\n'
        '<details>\n'
        '<summary style="cursor: pointer; font-size: 12px; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; color: var(--text)">'
        f'Text version of the family tree — all {n_people} people</summary>\n'
        f'<div style="margin-top: 18px">\n{intro}\n{body}\n</div>\n'
        '</details>\n'
        '</div>\n'
        f'{END}'
    )

    page = PAGE.read_text()
    pattern = re.escape(BEGIN) + r".*?" + re.escape(END)
    if not re.search(pattern, page, re.S):
        sys.exit("genealogy-static markers not found in genealogy.html")
    PAGE.write_text(re.sub(pattern, lambda _: block, page, flags=re.S))
    print(f"rendered {n_people} people, {len(block)} bytes of static HTML")


if __name__ == "__main__":
    main()
