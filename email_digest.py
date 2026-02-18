"""
Generates an HTML email digest of today's opportunities.
Compares current opportunities.json against the last known state
to highlight what's NEW since the last run.
"""
import json
import os
from datetime import datetime

def generate_digest():
    # Load current opportunities
    try:
        with open('opportunities.json') as f:
            opps = json.load(f)
    except FileNotFoundError:
        print("No opportunities.json found. Skipping digest.")
        return
    
    # Filter to active (non-deleted) opportunities
    active = [o for o in opps if o.get('status') != 'deleted']
    
    if not active:
        print("No active opportunities. Skipping email.")
        return
    
    # Separate by status
    new_opps = [o for o in active if not o.get('status')]
    do_opps = [o for o in active if o.get('status') == 'do']
    maybe_opps = [o for o in active if o.get('status') == 'maybe']
    
    today = datetime.now().strftime('%B %d, %Y')
    
    # Build HTML email
    html = f"""<!DOCTYPE html>
<html>
<head>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f1923; color: #e0e8f0; margin: 0; padding: 20px; }}
  .container {{ max-width: 600px; margin: 0 auto; }}
  h1 {{ color: #4fc3f7; font-size: 24px; margin-bottom: 4px; }}
  .date {{ color: #7a8a9a; font-size: 14px; margin-bottom: 24px; }}
  .summary {{ background: #1a2733; border-radius: 12px; padding: 16px; margin-bottom: 20px; }}
  .summary-row {{ display: flex; justify-content: space-between; padding: 6px 0; }}
  .summary-label {{ color: #7a8a9a; }}
  .summary-value {{ font-weight: 600; }}
  .card {{ background: #1a2733; border-radius: 12px; padding: 16px; margin-bottom: 12px; border-left: 4px solid #4fc3f7; }}
  .card.new {{ border-left-color: #22c55e; }}
  .card-title {{ font-size: 15px; font-weight: 600; margin-bottom: 8px; }}
  .card-meta {{ color: #7a8a9a; font-size: 13px; margin-bottom: 8px; }}
  .score {{ background: #4fc3f7; color: #0f1923; font-weight: 700; padding: 2px 8px; border-radius: 6px; font-size: 13px; }}
  .section-title {{ color: #4fc3f7; font-size: 16px; font-weight: 600; margin: 20px 0 10px; }}
  .overview {{ color: #b0bec5; font-size: 13px; line-height: 1.5; margin-top: 8px; }}
  .cta {{ display: inline-block; background: #4fc3f7; color: #0f1923; font-weight: 600; padding: 10px 20px; border-radius: 8px; text-decoration: none; margin-top: 20px; }}
</style>
</head>
<body>
<div class="container">
  <h1>AlphaStream Daily Digest</h1>
  <div class="date">{today}</div>
  
  <div class="summary">
    <div class="summary-row">
      <span class="summary-label">Total Active Opportunities</span>
      <span class="summary-value">{len(active)}</span>
    </div>
    <div class="summary-row">
      <span class="summary-label">👍 Committed</span>
      <span class="summary-value">{len(do_opps)}</span>
    </div>
    <div class="summary-row">
      <span class="summary-label">⭐ Watching</span>
      <span class="summary-value">{len(maybe_opps)}</span>
    </div>
    <div class="summary-row">
      <span class="summary-label">🆕 New Today</span>
      <span class="summary-value" style="color: #22c55e;">{len(new_opps)}</span>
    </div>
  </div>
"""
    
    if new_opps:
        html += '  <div class="section-title">🆕 New Opportunities</div>\n'
        for o in sorted(new_opps, key=lambda x: x.get('score', 0), reverse=True):
            html += _render_card(o, is_new=True)
    
    if do_opps:
        html += '  <div class="section-title">👍 Your Committed Items</div>\n'
        for o in sorted(do_opps, key=lambda x: x.get('score', 0), reverse=True):
            html += _render_card(o)
    
    if maybe_opps:
        html += '  <div class="section-title">⭐ Your Watchlist</div>\n'
        for o in sorted(maybe_opps, key=lambda x: x.get('score', 0), reverse=True):
            html += _render_card(o)
    
    html += """
  <a href="https://github.com/jht243/gov_biz_ideas" class="cta">View Full Dashboard →</a>
</div>
</body>
</html>"""
    
    with open('digest.html', 'w') as f:
        f.write(html)
    
    print(f"Email digest generated: {len(new_opps)} new, {len(do_opps)} committed, {len(maybe_opps)} watching")


def _render_card(opp, is_new=False):
    css_class = "card new" if is_new else "card"
    score = opp.get('score', '?')
    overview = opp.get('legislation_overview', opp.get('bill_description', ''))
    
    # Build score breakdown string
    bd = opp.get('score_breakdown', {})
    breakdown = ""
    if bd.get('market_size') is not None:
        breakdown = f"Mkt:{bd.get('market_size',0)}/25 · Conv:{bd.get('conversion_ease',0)}/25 · Pay:{bd.get('willingness_to_pay',0)}/20 · Build:{bd.get('build_feasibility',0)}/15 · Moat:{bd.get('competitive_moat',0)}/15"
    
    return f"""
  <div class="{css_class}">
    <div class="card-title">{opp.get('summary', opp.get('bill_title', 'Untitled'))}</div>
    <div class="card-meta">
      <span class="score">{score}/100</span> · {opp.get('state', '?')} · {opp.get('bill_id', '?')} · {opp.get('bill_status', 'Pending')}
    </div>
    {f'<div class="card-meta">{breakdown}</div>' if breakdown else ''}
    <div class="overview">{overview[:300]}{"..." if len(overview) > 300 else ""}</div>
  </div>
"""


if __name__ == '__main__':
    generate_digest()
