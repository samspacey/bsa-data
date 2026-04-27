"""Server-side PDF report generator (WeasyPrint).

Renders the Woodhurst Member Experience Benchmark as a one-page A4 PDF.
Matches the design in ``frontend/src/pages/PDFReport.tsx`` - same layout,
colours, typography - but produced from Python so we can attach the result
to an outbound email or serve it as a direct download.

WeasyPrint takes an HTML + CSS string and produces a PDF. It pulls fonts
from Google Fonts at render time (per the ``@import`` rule), so no font
files need to be bundled in the container.
"""

from __future__ import annotations

import base64
import html
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Optional


# The Woodhurst PNG ships in src/api/services/assets/ so it gets included in
# the Docker image's `COPY src /app/src` instruction. Loaded once and base64-
# encoded into a data URI so WeasyPrint embeds it directly without needing
# network access or a working file URL inside the container.
_LOGO_PATH = Path(__file__).parent / "assets" / "woodhurst-mark.png"


@lru_cache(maxsize=1)
def _logo_data_uri() -> str:
    """Return the Woodhurst logo as a `data:image/png;base64,...` URI.

    Cached so we only read + encode the file once per process. Falls back to
    an empty string if the asset is missing - the layout still renders, just
    without the logo image.
    """
    try:
        b = _LOGO_PATH.read_bytes()
        return "data:image/png;base64," + base64.b64encode(b).decode("ascii")
    except FileNotFoundError:
        return ""


@dataclass
class ReportScore:
    factor: str
    score: float
    avg: float
    rank: int
    status: str  # "above" | "near" | "below"


# Default scores - these match the hardcoded data in BenchmarkModal.tsx so
# the download and email paths produce the same numbers as the on-screen
# preview. Swap for real computed scores when we wire that up.
DEFAULT_SCORES: list[ReportScore] = [
    ReportScore("Customer Service",    8.2, 7.1, 9,  "above"),
    ReportScore("Digital Experience",  5.1, 6.8, 34, "below"),
    ReportScore("Branch Experience",   9.1, 7.3, 3,  "above"),
    ReportScore("Mortgage Products",   6.9, 7.0, 21, "near"),
    ReportScore("Savings Rates",       6.2, 7.2, 29, "below"),
    ReportScore("Communication",       7.4, 7.1, 14, "near"),
    ReportScore("Local Community",     9.4, 6.9, 2,  "above"),
]


def _ordinal(n: int) -> str:
    suffixes = ["th", "st", "nd", "rd"]
    v = n % 100
    suffix = suffixes[(v - 20) % 10] if (v - 20) % 10 < 4 else suffixes[v] if v < 4 else suffixes[0]
    return f"{n}{suffix}"


_STATUS = {
    "above": {"color": "#2E8B6B", "soft": "#D6EDE2", "label": "Above avg"},
    "near":  {"color": "#C08A2E", "soft": "#F4E7CC", "label": "Near avg"},
    "below": {"color": "#E84560", "soft": "#FFE1E6", "label": "Below avg"},
}


def _render_html(
    society_name: str,
    society_region: str,
    scores: list[ReportScore],
    recommendations: list[str],
    generated_on: date,
    quote: str,
    quote_source: str,
) -> str:
    """Build the full HTML document for WeasyPrint."""

    above_count = sum(1 for s in scores if s.status == "above")
    below_count = sum(1 for s in scores if s.status == "below")
    above_only = [s for s in scores if s.status == "above"]
    below_only = [s for s in scores if s.status == "below"]
    top_strength = max(above_only, key=lambda s: s.score) if above_only else None
    biggest_gap = min(below_only, key=lambda s: s.score) if below_only else None

    overall_v = (
        f"Above avg on {above_count} of {len(scores)}" if above_count > 0
        else f"Parity or below on all {len(scores)}"
    )
    top_v = f"{top_strength.factor} · {top_strength.score:.1f}" if top_strength else "No factor clearly above avg"
    gap_v = (
        f"{biggest_gap.factor} · {biggest_gap.score:.1f}" if biggest_gap
        else f"{below_count} factor{'s' if below_count != 1 else ''} below avg"
    )

    today_str = generated_on.strftime("%-d %B %Y")
    logo_uri = _logo_data_uri()

    # Rows of the scores table. Inline bars drawn via CSS widths.
    rows_html: list[str] = []
    for i, s in enumerate(scores):
        st = _STATUS[s.status]
        pct = (s.score / 10) * 100
        avg_pct = (s.avg / 10) * 100
        bg = "#FFFFFF" if i % 2 == 0 else "#FAFAFC"
        rows_html.append(f"""
          <tr style="background: {bg};">
            <td class="factor">{html.escape(s.factor)}</td>
            <td class="score">{s.score:.1f}</td>
            <td class="avg">{s.avg:.1f}</td>
            <td class="bar-cell">
              <div class="bar-track">
                <div class="bar-fill" style="width: {pct:.1f}%; background: {st['color']};"></div>
                <div class="bar-avg" style="left: {avg_pct:.1f}%;"></div>
              </div>
            </td>
            <td class="rank">{_ordinal(s.rank)}</td>
            <td class="status">
              <span class="status-pill" style="color: {st['color']}; background: {st['soft']};">
                {st['label'].upper()}
              </span>
            </td>
          </tr>
        """)

    recs_html: list[str] = []
    for i, r in enumerate(recommendations):
        last = i == len(recommendations) - 1
        border = "" if last else "border-bottom: 1px solid #E1E3EE;"
        recs_html.append(f"""
          <li style="{border}">
            <span class="rec-num">{i+1:02d}</span>
            <span>{html.escape(r)}</span>
          </li>
        """)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{
  margin: 0; padding: 0;
  font-family: 'Montserrat', Arial, sans-serif;
  color: #0F1033;
  background: #FFFFFF;
  -webkit-font-smoothing: antialiased;
}}
.page {{
  width: 210mm; min-height: 297mm;
  padding: 52px 56px 40px;
  position: relative;
  background: #FFFFFF;
}}
.rule-top {{ position: absolute; top: 0; left: 0; right: 0; height: 8px; background: #1E205F; }}
.mono {{
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 11px; letter-spacing: 0.06em;
  text-transform: uppercase;
}}
.eyebrow {{
  font-size: 11px; font-weight: 600; letter-spacing: 0.14em;
  text-transform: uppercase; color: #6B6E95;
}}
.num {{ font-variant-numeric: tabular-nums; }}

.masthead {{
  display: flex; justify-content: space-between; align-items: flex-start;
  padding-bottom: 20px; border-bottom: 1px solid #E1E3EE;
}}
.mark {{
  display: flex; align-items: center; gap: 10px;
  font-size: 16px; font-weight: 800; color: #1E205F; letter-spacing: -0.015em;
}}
.mark-icon {{
  display: inline-block; line-height: 0;
}}
.mark-icon img {{
  height: 24px; width: auto; display: block;
}}
.mark-text {{
  font-family: 'Montserrat', Arial, sans-serif;
  font-size: 16px; font-weight: 800; color: #1E205F; letter-spacing: -0.015em;
}}
.dateline {{ text-align: right; font-size: 10px; color: #6B6E95; }}
.dateline .title {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; color: #1E205F; letter-spacing: 0.06em; text-transform: uppercase; }}

.headline {{ margin-top: 28px; margin-bottom: 24px; }}
.headline .label {{ color: #FF5773; margin-bottom: 10px; }}
.headline h1 {{
  font-size: 38px; font-weight: 800; letter-spacing: -0.03em;
  margin: 0; line-height: 1.05; color: #1E205F;
}}
.headline .sub {{ font-size: 12.5px; color: #6B6E95; margin-top: 8px; }}

.summary {{
  background: #F4F5FA; border: 1px solid #E1E3EE; border-radius: 8px;
  padding: 18px 22px;
  display: flex; gap: 20px;
  margin-bottom: 26px;
}}
.summary-item {{ flex: 1; padding-left: 0; }}
.summary-item + .summary-item {{ padding-left: 18px; border-left: 1px solid #E1E3EE; }}
.summary-item .eyebrow {{ font-size: 9px; }}
.summary-item .value {{
  font-size: 13px; font-weight: 700; color: #1E205F;
  margin-top: 4px; letter-spacing: -0.01em;
}}

table.scores {{
  width: 100%; border-collapse: collapse;
  border: 1px solid #E1E3EE; border-radius: 6px; overflow: hidden;
  table-layout: fixed;
}}
table.scores thead th {{
  font-size: 9px; font-weight: 700; color: #6B6E95;
  letter-spacing: 0.08em; text-transform: uppercase;
  padding: 9px 14px; background: #F2F3F8; text-align: left;
}}
table.scores tbody td {{
  font-size: 11.5px; padding: 11px 14px;
  border-top: 1px solid #E1E3EE; vertical-align: middle;
}}
table.scores td.factor {{ font-weight: 700; color: #1E205F; }}
table.scores td.score {{ text-align: center; font-weight: 800; color: #1E205F; font-variant-numeric: tabular-nums; }}
table.scores td.avg {{ text-align: center; color: #6B6E95; font-variant-numeric: tabular-nums; }}
table.scores td.rank {{ text-align: center; font-size: 10.5px; color: #3A3C6A; font-weight: 600; font-variant-numeric: tabular-nums; }}
table.scores td.status {{ text-align: center; }}
.bar-cell {{ padding: 11px 14px; }}
.bar-track {{ position: relative; height: 9px; background: #E8EAF2; border-radius: 2px; }}
.bar-fill  {{ position: absolute; top: 0; bottom: 0; left: 0; border-radius: 2px; }}
.bar-avg   {{ position: absolute; top: -2px; bottom: -2px; width: 1.5px; background: #0F1033; }}
.status-pill {{
  font-size: 9px; font-weight: 700; padding: 2px 7px;
  border-radius: 3px; white-space: nowrap;
}}

.scores-label {{ margin-bottom: 10px; }}

.quote-recs {{
  margin-top: 26px;
  display: flex; gap: 20px;
}}
.quote {{
  flex: 1;
  background: #1E205F; color: #FFFFFF;
  border-radius: 8px; padding: 20px 22px;
}}
.quote .mark-quote {{
  color: #FF5773;
  font-size: 26px; line-height: 1; margin-bottom: 6px; font-weight: 800;
}}
.quote p {{
  font-size: 14px; line-height: 1.4; margin: 0;
  font-weight: 500; letter-spacing: -0.01em;
}}
.quote .attribution {{
  margin-top: 16px; font-size: 10px; color: rgba(255,255,255,0.6);
  border-top: 1px solid rgba(255,255,255,0.2); padding-top: 10px;
}}
.recs {{ flex: 1.1; }}
.recs ol {{
  margin: 0; padding: 0; list-style: none;
  font-size: 11.5px; line-height: 1.55; color: #3A3C6A;
}}
.recs li {{
  display: flex; gap: 10px;
  margin-bottom: 10px; padding-bottom: 10px;
}}
.rec-num {{
  font-weight: 800; color: #FF5773; font-size: 14px;
  min-width: 22px; font-variant-numeric: tabular-nums;
}}

.footer {{
  position: absolute; bottom: 24px; left: 56px; right: 56px;
  padding-top: 14px; border-top: 1px solid #E1E3EE;
  display: flex; justify-content: space-between;
  font-size: 9.5px; color: #9B9DBA;
}}
.footer .mono {{ font-size: 9.5px; }}
</style>
</head>
<body>
  <div class="page">
    <div class="rule-top"></div>

    <div class="masthead">
      <div class="mark">
        <span class="mark-icon">
          {f'<img src="{logo_uri}" alt="Woodhurst">' if logo_uri else '<span class="mark-text">Woodhurst</span>'}
        </span>
      </div>
      <div class="dateline">
        <div class="title">MEMBER EXPERIENCE BENCHMARK</div>
        <div>{html.escape(today_str)} · Confidential</div>
      </div>
    </div>

    <div class="headline">
      <div class="eyebrow label">Report for</div>
      <h1>{html.escape(society_name)}</h1>
      <div class="sub">{html.escape(society_region)} · benchmarked against 42 UK building societies</div>
    </div>

    <div class="summary">
      <div class="summary-item">
        <div class="eyebrow" style="color: #1E205F;">Overall position</div>
        <div class="value">{html.escape(overall_v)}</div>
      </div>
      <div class="summary-item">
        <div class="eyebrow" style="color: #2E8B6B;">Top strength</div>
        <div class="value">{html.escape(top_v)}</div>
      </div>
      <div class="summary-item">
        <div class="eyebrow" style="color: #E84560;">Biggest gap</div>
        <div class="value">{html.escape(gap_v)}</div>
      </div>
    </div>

    <div class="eyebrow scores-label">Scores by factor</div>
    <table class="scores">
      <thead>
        <tr>
          <th style="width: 28%;">Factor</th>
          <th style="width: 9%; text-align: center;">Score</th>
          <th style="width: 8%; text-align: center;">Avg</th>
          <th style="width: 28%;">vs Industry (0-10)</th>
          <th style="width: 10%; text-align: center;">Rank</th>
          <th style="width: 17%; text-align: center;">Status</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows_html)}
      </tbody>
    </table>

    <div class="quote-recs">
      <div class="quote">
        <div class="mark-quote">&ldquo;</div>
        <p>{html.escape(quote)}</p>
        <div class="attribution">{html.escape(quote_source)}</div>
      </div>
      <div class="recs">
        <div class="eyebrow" style="margin-bottom: 10px;">Recommended focus</div>
        <ol>
          {''.join(recs_html)}
        </ol>
      </div>
    </div>

    <div class="footer">
      <span>Woodhurst Consulting · Data &amp; Digital Advisory</span>
      <span class="mono">CONFIDENTIAL · PAGE 01 / 01</span>
    </div>
  </div>
</body>
</html>"""


DEFAULT_RECOMMENDATIONS = [
    "Protect branch experience for members whose relationship with the society is anchored there.",
    "Close the digital gap: app and sign-in flows are the biggest friction in recent reviews.",
    "Lead communications with community narrative, it is your most under-expressed strength.",
]

# Used only when the route can't pull a real quote (e.g. no enrichment yet).
DEFAULT_QUOTE = (
    "Members value the branch relationships most. Loyalty rates could be sharper."
)
DEFAULT_QUOTE_SOURCE = "Composite quote drawn from recent member reviews"


def render_report_pdf(
    society_name: str,
    society_region: str,
    scores: Optional[list[ReportScore]] = None,
    recommendations: Optional[list[str]] = None,
    generated_on: Optional[date] = None,
    quote: Optional[str] = None,
    quote_source: Optional[str] = None,
) -> bytes:
    """Render the benchmark report as PDF bytes.

    ``quote`` / ``quote_source`` should be supplied by the caller from
    ``report_narrative.pick_representative_quote()`` so each society's PDF
    quotes a real review from that society's corpus rather than the same
    composite line. Falls back to the generic composite if the caller passes
    ``None`` (e.g. the society has no enrichment data yet).

    Raises RuntimeError if WeasyPrint isn't installed in the environment
    (the Docker image installs it; local dev might not).
    """
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise RuntimeError(
            "weasyprint is not installed. Add it to pyproject.toml and rebuild."
        ) from exc

    html_doc = _render_html(
        society_name=society_name,
        society_region=society_region,
        scores=scores or DEFAULT_SCORES,
        recommendations=recommendations or DEFAULT_RECOMMENDATIONS,
        generated_on=generated_on or date.today(),
        quote=quote or DEFAULT_QUOTE,
        quote_source=quote_source or DEFAULT_QUOTE_SOURCE,
    )
    return HTML(string=html_doc).write_pdf()
