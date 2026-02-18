"""
Generates an HTML email digest of today's opportunities.
Uses table-based layout with inline styles for email client compatibility.
"""
import json
import os
from datetime import datetime


def generate_digest():
    try:
        with open('opportunities.json') as f:
            opps = json.load(f)
    except FileNotFoundError:
        print("No opportunities.json found. Skipping digest.")
        return

    active = [o for o in opps if o.get('status') != 'deleted']
    if not active:
        print("No active opportunities. Skipping email.")
        return

    new_opps = [o for o in active if not o.get('status')]
    do_opps = [o for o in active if o.get('status') == 'do']
    maybe_opps = [o for o in active if o.get('status') == 'maybe']

    today = datetime.now().strftime('%B %d, %Y')

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background-color:#0f1923; font-family:Arial, Helvetica, sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f1923;">
<tr><td align="center" style="padding:20px;">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px; width:100%;">

  <!-- Header -->
  <tr><td style="padding:20px 0 4px;">
    <h1 style="margin:0; font-size:26px; color:#4fc3f7; font-weight:700;">⚡ AlphaStream Daily Digest</h1>
  </td></tr>
  <tr><td style="padding:0 0 20px; font-size:14px; color:#7a8a9a;">{today}</td></tr>

  <!-- Summary Box -->
  <tr><td style="background-color:#1a2733; border-radius:12px; padding:20px; margin-bottom:20px;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:6px 0; color:#7a8a9a; font-size:14px;">Total Active</td>
        <td style="padding:6px 0; text-align:right; font-size:14px; font-weight:600; color:#e0e8f0;">{len(active)}</td>
      </tr>
      <tr>
        <td style="padding:6px 0; color:#7a8a9a; font-size:14px;">👍 Committed</td>
        <td style="padding:6px 0; text-align:right; font-size:14px; font-weight:600; color:#e0e8f0;">{len(do_opps)}</td>
      </tr>
      <tr>
        <td style="padding:6px 0; color:#7a8a9a; font-size:14px;">⭐ Watching</td>
        <td style="padding:6px 0; text-align:right; font-size:14px; font-weight:600; color:#e0e8f0;">{len(maybe_opps)}</td>
      </tr>
      <tr>
        <td style="padding:6px 0; color:#7a8a9a; font-size:14px;">🆕 New Today</td>
        <td style="padding:6px 0; text-align:right; font-size:14px; font-weight:600; color:#22c55e;">{len(new_opps)}</td>
      </tr>
    </table>
  </td></tr>

  <tr><td style="height:16px;"></td></tr>
"""

    if new_opps:
        html += _section_header('🆕 New Opportunities')
        for o in sorted(new_opps, key=lambda x: x.get('score', 0), reverse=True):
            html += _render_card(o, border_color='#22c55e')

    if do_opps:
        html += _section_header('👍 Your Committed Items')
        for o in sorted(do_opps, key=lambda x: x.get('score', 0), reverse=True):
            html += _render_card(o, border_color='#4fc3f7')

    if maybe_opps:
        html += _section_header('⭐ Your Watchlist')
        for o in sorted(maybe_opps, key=lambda x: x.get('score', 0), reverse=True):
            html += _render_card(o, border_color='#eab308')

    html += """
  <!-- Footer -->
  <tr><td style="padding:24px 0; text-align:center;">
    <a href="https://github.com/jht243/gov_biz_ideas" style="display:inline-block; background-color:#4fc3f7; color:#0f1923; font-weight:700; padding:12px 28px; border-radius:8px; text-decoration:none; font-size:14px;">View Full Dashboard →</a>
  </td></tr>
  <tr><td style="padding:10px 0; text-align:center; font-size:12px; color:#4a5568;">
    AlphaStream · Automated Legislative Intelligence
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    with open('digest.html', 'w') as f:
        f.write(html)

    print(f"Email digest generated: {len(new_opps)} new, {len(do_opps)} committed, {len(maybe_opps)} watching")


def _section_header(title):
    return f"""
  <tr><td style="padding:16px 0 8px;">
    <h2 style="margin:0; font-size:17px; color:#4fc3f7; font-weight:600;">{title}</h2>
  </td></tr>
"""


def _render_card(opp, border_color='#4fc3f7'):
    score = opp.get('score', '?')
    overview = opp.get('legislation_overview', opp.get('bill_description', ''))
    if len(overview) > 250:
        overview = overview[:250] + '...'

    # Score breakdown bars
    bd = opp.get('score_breakdown', {})
    bars_html = ''
    if bd.get('market_size') is not None:
        bars = [
            ('Market Size', bd.get('market_size', 0), 25),
            ('Conversion', bd.get('conversion_ease', 0), 25),
            ('Will. to Pay', bd.get('willingness_to_pay', 0), 20),
            ('Buildability', bd.get('build_feasibility', 0), 15),
            ('Moat', bd.get('competitive_moat', 0), 15),
        ]
        bars_html = '<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:12px;">'
        for label, val, mx in bars:
            pct = round((val / mx) * 100)
            color = '#22c55e' if pct >= 75 else '#eab308' if pct >= 50 else '#ef4444'
            bars_html += f"""
            <tr>
              <td style="width:90px; padding:3px 0; font-size:11px; color:#7a8a9a;">{label}</td>
              <td style="padding:3px 8px;">
                <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#2a3744; border-radius:4px; height:7px;">
                  <tr><td style="width:{pct}%; background-color:{color}; border-radius:4px; height:7px;"></td><td></td></tr>
                </table>
              </td>
              <td style="width:40px; text-align:right; padding:3px 0; font-size:11px; font-weight:600; color:{color};">{val}/{mx}</td>
            </tr>"""
        bars_html += '</table>'

    summary = opp.get('summary', opp.get('bill_title', 'Untitled'))

    return f"""
  <tr><td style="padding:6px 0;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#1a2733; border-radius:12px; border-left:4px solid {border_color};">
      <tr><td style="padding:16px 18px;">

        <!-- Title -->
        <div style="font-size:15px; font-weight:600; color:#e0e8f0; margin-bottom:8px; line-height:1.4;">{summary}</div>

        <!-- Meta -->
        <div style="margin-bottom:10px;">
          <span style="display:inline-block; background-color:#4fc3f7; color:#0f1923; font-weight:700; padding:2px 8px; border-radius:6px; font-size:12px;">{score}/100</span>
          <span style="color:#7a8a9a; font-size:13px; margin-left:8px;">{opp.get('state', '?')} · {opp.get('bill_id', '?')} · {opp.get('bill_status', 'Pending')}</span>
        </div>

        <!-- Overview -->
        <div style="font-size:13px; color:#b0bec5; line-height:1.6; margin-bottom:4px;">{overview}</div>

        <!-- Score Bars -->
        {bars_html}

      </td></tr>
    </table>
  </td></tr>
"""


if __name__ == '__main__':
    generate_digest()
