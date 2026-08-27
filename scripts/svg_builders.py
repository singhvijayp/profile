"""
Shared SVG-building functions for the profile stat graphics.

Design notes (kept from the original repo this was cloned from):
- No external assets. Every graphic here is a self-contained <svg> with
  inline styles, because GitHub strips <style> blocks and scripts from
  READMEs, and strips most CSS everywhere else too.
- Font: these use a generic monospace stack (JetBrains Mono, Fira Code,
  Consolas, monospace) instead of an embedded/subset font. The original
  repo base64-inlines a subset of JetBrains Mono so the exact glyph
  widths are guaranteed across viewers -- if you want that level of
  polish, add a font-subsetting step here (fonttools `pyftsubset`) and
  swap the <text> font-family for an embedded @font-face-free approach
  (SVG <text> can't easily use @font-face once CSS is stripped, so the
  original renders each glyph as a <path> -- more work, bigger payoff).
- Colors are chosen to read reasonably on both light and dark GitHub
  themes rather than using `prefers-color-scheme`, since that also
  requires a <style> block GitHub will strip on avatar-adjacent pages.
"""

FONT_STACK = "'JetBrains Mono','Fira Code',Consolas,monospace"

BG = "#0d1117"
FG = "#c9d1d9"
MUTED = "#8b949e"
ACCENT = "#58a6ff"
GOOD = "#3fb950"
WARN = "#d29922"
BORDER = "#30363d"


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def svg_wrap(width: int, height: int, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">'
        f'<rect width="{width}" height="{height}" rx="10" fill="{BG}" '
        f'stroke="{BORDER}" stroke-width="1"/>'
        f"{body}</svg>"
    )


def heading(label: str, width: int = 860, height: int = 46) -> str:
    """A section heading rendered as an image (e.g. '// about')."""
    label = _escape(label)
    body = (
        f'<text x="24" y="30" font-family="{FONT_STACK}" font-size="20" '
        f'font-weight="700" fill="{ACCENT}">'
        f'<tspan fill="{MUTED}">// </tspan>{label}'
        f"</text>"
        f'<line x1="24" y1="40" x2="{width - 24}" y2="40" stroke="{BORDER}" stroke-width="1"/>'
    )
    return svg_wrap(width, height, body)


def stat_card(title: str, stats: list, width: int = 420, height: int = 190) -> str:
    """stats: list of (label, value) tuples."""
    body = [
        f'<text x="24" y="34" font-family="{FONT_STACK}" font-size="16" '
        f'font-weight="700" fill="{FG}">{_escape(title)}</text>'
    ]
    y = 70
    for label, value in stats:
        body.append(
            f'<text x="24" y="{y}" font-family="{FONT_STACK}" font-size="13" '
            f'fill="{MUTED}">{_escape(label)}</text>'
        )
        body.append(
            f'<text x="{width - 24}" y="{y}" text-anchor="end" '
            f'font-family="{FONT_STACK}" font-size="13" font-weight="700" '
            f'fill="{FG}">{_escape(str(value))}</text>'
        )
        y += 28
    return svg_wrap(width, height, "".join(body))


def streak_card(current: int, longest: int, total: int, width: int = 700, height: int = 180) -> str:
    col_w = width / 3
    cols = [
        ("Current Streak", current, GOOD),
        ("Total Contributions", total, ACCENT),
        ("Longest Streak", longest, WARN),
    ]
    body = []
    for i, (label, value, color) in enumerate(cols):
        cx = int(col_w * i + col_w / 2)
        body.append(
            f'<text x="{cx}" y="80" text-anchor="middle" font-family="{FONT_STACK}" '
            f'font-size="34" font-weight="700" fill="{color}">{value}</text>'
        )
        body.append(
            f'<text x="{cx}" y="108" text-anchor="middle" font-family="{FONT_STACK}" '
            f'font-size="12" fill="{MUTED}">{_escape(label)}</text>'
        )
        if i > 0:
            x = int(col_w * i)
            body.append(
                f'<line x1="{x}" y1="30" x2="{x}" y2="150" stroke="{BORDER}" stroke-width="1"/>'
            )
    return svg_wrap(width, height, "".join(body))


def lang_bar(languages: list, width: int = 700, height: int = 240) -> str:
    """languages: list of (name, pct, color) sorted desc, pct sums to <=100."""
    body = [
        f'<text x="24" y="34" font-family="{FONT_STACK}" font-size="16" '
        f'font-weight="700" fill="{FG}">Top Languages</text>'
    ]
    bar_x, bar_y, bar_w, bar_h = 24, 54, width - 48, 14
    x = bar_x
    for name, pct, color in languages:
        seg_w = bar_w * (pct / 100.0)
        body.append(f'<rect x="{x:.1f}" y="{bar_y}" width="{seg_w:.1f}" height="{bar_h}" fill="{color}"/>')
        x += seg_w
    y = bar_y + bar_h + 30
    col = 0
    row_h = 24
    for i, (name, pct, color) in enumerate(languages):
        cx = bar_x + (col * (width - 48) / 2)
        body.append(f'<circle cx="{cx + 6}" cy="{y - 5}" r="5" fill="{color}"/>')
        body.append(
            f'<text x="{cx + 18}" y="{y}" font-family="{FONT_STACK}" font-size="12" '
            f'fill="{FG}">{_escape(name)} <tspan fill="{MUTED}">{pct:.1f}%</tspan></text>'
        )
        col += 1
        if col == 2:
            col = 0
            y += row_h
    return svg_wrap(width, max(height, y + 20), "".join(body))


def year_ramp(day_levels: list, width: int = 900, height: int = 160) -> str:
    """
    day_levels: list of ints 0-3 (quiet -> loud), one per day, oldest first.
    Rendered as text characters ':' '+' '#' '@' in a 7-row x N-col grid,
    matching the GitHub contribution graph layout (columns = weeks).
    """
    ramp = [":", "+", "#", "@"]
    colors = [MUTED, "#2ea043", GOOD, ACCENT]
    weeks = [day_levels[i:i + 7] for i in range(0, len(day_levels), 7)]
    cell = 12
    ox, oy = 20, 30
    body = [
        f'<text x="{ox}" y="18" font-family="{FONT_STACK}" font-size="11" '
        f'fill="{MUTED}">the last year, one character per day</text>'
    ]
    for col, week in enumerate(weeks):
        for row, level in enumerate(week):
            ch = ramp[level]
            color = colors[level]
            x = ox + col * cell
            y = oy + row * cell
            body.append(
                f'<text x="{x}" y="{y}" font-family="{FONT_STACK}" font-size="12" '
                f'fill="{color}">{ch}</text>'
            )
    computed_width = ox + len(weeks) * cell + 20
    computed_height = oy + 7 * cell + 10
    return svg_wrap(max(width, computed_width), max(height, computed_height), "".join(body))
