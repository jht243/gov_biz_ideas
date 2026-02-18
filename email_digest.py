"""
Generates an HTML email digest of today's opportunities.
Focuses on NEW items. Committed and watchlist shown as brief footnote.
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

    new_opps = [o for o in active if not o.get('seen') and not o.get('status')]
    do_opps = [o for o in active if o.get('status') == 'do']
    maybe_opps = [o for o in active if o.get('status') == 'maybe']

    today = datetime.now().strftime('%B %d, %Y')

    # If nothing new, send a short "no new items" email
    if not new_opps:
        html = _build_no_new_email(today, do_opps, maybe_opps)
    else:
        html = _build_new_items_email(today, new_opps, do_opps, maybe_opps)

    with open('digest.html', 'w') as f:
        f.write(html)

    print(f"Email digest generated: {len(new_opps)} new, {len(do_opps)} committed, {len(maybe_opps)} watching")


def _build_no_new_email(today, do_opps, maybe_opps):
    # Build clean title lists
    committed_html = ''
    if do_opps:
        committed_html = '<div style="text-align:left; margin-top:16px;">'
        committed_html += '<div style="font-size:13px; color:#4fc3f7; font-weight:600; margin-bottom:10px;">👍 Your Committed Items</div>'
        for o in do_opps:
            title = o.get('summary', o.get('bill_title', ''))[:90]
            committed_html += f'<div style="font-size:13px; color:#e0e8f0; padding:6px 0; border-bottom:1px solid #2a3744;">• {title}</div>'
        committed_html += '</div>'

    watchlist_html = ''
    if maybe_opps:
        watchlist_html = '<div style="text-align:left; margin-top:14px;">'
        watchlist_html += '<div style="font-size:13px; color:#eab308; font-weight:600; margin-bottom:10px;">⭐ Your Watchlist</div>'
        for o in maybe_opps:
            title = o.get('summary', o.get('bill_title', ''))[:90]
            watchlist_html += f'<div style="font-size:13px; color:#e0e8f0; padding:6px 0; border-bottom:1px solid #2a3744;">• {title}</div>'
        watchlist_html += '</div>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background-color:#0f1923; font-family:Arial, Helvetica, sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f1923;">
<tr><td align="center" style="padding:20px;">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px; width:100%;">
  <tr><td style="padding:20px 0 4px;">
    <h1 style="margin:0; font-size:24px; color:#4fc3f7; font-weight:700;">⚡ AlphaStream Daily Digest</h1>
  </td></tr>
  <tr><td style="padding:0 0 20px; font-size:14px; color:#7a8a9a;">{today}</td></tr>
  <tr><td style="background-color:#1a2733; border-radius:12px; padding:24px;">
    <div style="font-size:16px; color:#e0e8f0; margin-bottom:4px; text-align:center;">No new opportunities today.</div>
    {committed_html}
    {watchlist_html}
  </td></tr>
  <tr><td style="padding:16px 0; text-align:center;">
    <a href="https://github.com/jht243/gov_biz_ideas" style="display:inline-block; background-color:#4fc3f7; color:#0f1923; font-weight:700; padding:10px 24px; border-radius:8px; text-decoration:none; font-size:13px;">View Dashboard →</a>
  </td></tr>
  <tr><td style="padding:4px 0; text-align:center; font-size:11px; color:#4a5568;">AlphaStream · Automated Legislative Intelligence</td></tr>
</table></td></tr></table>
</body></html>"""


def _build_new_items_email(today, new_opps, do_opps, maybe_opps):
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background-color:#0f1923; font-family:Arial, Helvetica, sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f1923;">
<tr><td align="center" style="padding:20px;">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px; width:100%;">

  <!-- Header -->
  <tr><td style="padding:20px 0 4px;">
    <h1 style="margin:0; font-size:24px; color:#4fc3f7; font-weight:700;">⚡ AlphaStream Daily Digest</h1>
  </td></tr>
  <tr><td style="padding:0 0 16px; font-size:14px; color:#7a8a9a;">{today}</td></tr>

  <!-- New count banner -->
  <tr><td style="background-color:#22c55e; border-radius:8px; padding:12px 18px; margin-bottom:16px;">
    <div style="font-size:16px; font-weight:700; color:#fff;">🆕 {len(new_opps)} New Opportunit{'y' if len(new_opps) == 1 else 'ies'} Found</div>
  </td></tr>

  <tr><td style="height:12px;"></td></tr>
"""

    # Render each new opportunity as a full card
    for o in sorted(new_opps, key=lambda x: x.get('score', 0), reverse=True):
        html += _render_card(o)

    # Footer with existing committed/watchlist as brief list
    if do_opps or maybe_opps:
        html += """<tr><td style="height:20px;"></td></tr>
  <tr><td style="border-top:1px solid #2a3744; padding-top:16px;">"""

        if do_opps:
            html += '<div style="font-size:13px; color:#7a8a9a; margin-bottom:8px;">👍 <strong style="color:#b0bec5;">Committed</strong></div>'
            for o in do_opps:
                html += f'<div style="font-size:12px; color:#7a8a9a; padding:2px 0;">• {o.get("summary", o.get("bill_title", ""))[:80]} ({o.get("state")} {o.get("bill_id")})</div>'

        if maybe_opps:
            html += '<div style="font-size:13px; color:#7a8a9a; margin-bottom:8px; margin-top:10px;">⭐ <strong style="color:#b0bec5;">Watchlist</strong></div>'
            for o in maybe_opps:
                html += f'<div style="font-size:12px; color:#7a8a9a; padding:2px 0;">• {o.get("summary", o.get("bill_title", ""))[:80]} ({o.get("state")} {o.get("bill_id")})</div>'

        html += '</td></tr>'

    html += """
  <tr><td style="padding:20px 0; text-align:center;">
    <a href="https://github.com/jht243/gov_biz_ideas" style="display:inline-block; background-color:#4fc3f7; color:#0f1923; font-weight:700; padding:12px 28px; border-radius:8px; text-decoration:none; font-size:14px;">Review on Dashboard →</a>
  </td></tr>
  <tr><td style="padding:8px 0; text-align:center; font-size:11px; color:#4a5568;">AlphaStream · Automated Legislative Intelligence</td></tr>
</table></td></tr></table>
</body></html>"""

    return html


def _render_card(opp):
    score = opp.get('score', '?')
    overview = opp.get('legislation_overview', opp.get('bill_description', ''))
    if len(overview) > 280:
        overview = overview[:280] + '...'

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
              <td style="width:85px; padding:3px 0; font-size:11px; color:#7a8a9a;">{label}</td>
              <td style="padding:3px 8px;">
                <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#2a3744; border-radius:4px; height:7px;">
                  <tr><td style="width:{pct}%; background-color:{color}; border-radius:4px; height:7px;"></td><td></td></tr>
                </table>
              </td>
              <td style="width:36px; text-align:right; padding:3px 0; font-size:11px; font-weight:600; color:{color};">{val}/{mx}</td>
            </tr>"""
        bars_html += '</table>'

    return f"""
  <tr><td style="padding:6px 0;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#1a2733; border-radius:12px; border-left:4px solid #22c55e;">
      <tr><td style="padding:16px 18px;">
        <div style="font-size:15px; font-weight:600; color:#e0e8f0; margin-bottom:8px; line-height:1.4;">
          <span style="display:inline-block; background:#22c55e; color:#fff; font-size:10px; font-weight:700; padding:2px 6px; border-radius:3px; margin-right:6px; vertical-align:middle;">NEW</span>
          {opp.get('summary', opp.get('bill_title', 'Untitled'))}
        </div>
        <div style="margin-bottom:10px;">
          <span style="display:inline-block; background-color:#4fc3f7; color:#0f1923; font-weight:700; padding:2px 8px; border-radius:6px; font-size:12px;">{score}/100</span>
          <span style="color:#7a8a9a; font-size:13px; margin-left:8px;">{opp.get('state', '?')} · {opp.get('bill_id', '?')} · {opp.get('bill_status', 'Pending')}</span>
        </div>
        <div style="font-size:13px; color:#b0bec5; line-height:1.6;">{overview}</div>
        {bars_html}
      </td></tr>
    </table>
  </td></tr>
"""


if __name__ == '__main__':
    generate_digest()
