from flask import Flask, render_template, jsonify, request
import json
import os
from main import generate_opportunity_report

app = Flask(__name__)
DATA_FILE = 'opportunities.json'
REPORT_FILE = 'opportunity_report.md'

def load_opportunities():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def save_opportunities(opportunities):
    with open(DATA_FILE, 'w') as f:
        json.dump(opportunities, f, indent=2)
    
    # Regenerate the markdown report
    # Only include items that are NOT marked as 'deleted'
    # 'Do' and 'Maybe' items potentially go into different sections or stay?
    # For now, let's keep all non-deleted items in the report, maybe grouped?
    # User asked: "if i thumbs down, it will delete from the html and also from the report.md"
    # So we simply filter out deleted items.
    
    active_opps = [o for o in opportunities if o.get('status') != 'deleted']
    generate_opportunity_report(active_opps, REPORT_FILE)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/opportunities', methods=['GET'])
def get_opportunities():
    opps = load_opportunities()
    # Filter out deleted items for the UI
    active_opps = [o for o in opps if o.get('status') != 'deleted']
    return jsonify(active_opps)

@app.route('/api/mark-seen', methods=['POST'])
def mark_seen():
    """Mark all unseen items as seen. Called after user views the dashboard."""
    opps = load_opportunities()
    count = 0
    for o in opps:
        if o.get('status') != 'deleted' and not o.get('seen'):
            o['seen'] = True
            count += 1
    if count > 0:
        save_opportunities(opps)
    return jsonify({"marked": count})

@app.route('/api/action', methods=['POST'])
def handle_action():
    data = request.json
    bill_id = data.get('bill_id')
    state = data.get('state')
    action = data.get('action') # 'do', 'maybe', 'delete'
    
    if not all([bill_id, state, action]):
        return jsonify({"error": "Missing data"}), 400
        
    opportunities = load_opportunities()
    updated = False
    
    for opp in opportunities:
        if opp.get('bill_id') == bill_id and opp.get('state') == state:
            if action == 'delete':
                opp['status'] = 'deleted'
            elif action == 'do':
                opp['status'] = 'do'
            elif action == 'maybe':
                opp['status'] = 'maybe'
            updated = True
            break
            
    if updated:
        save_opportunities(opportunities)
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Opportunity not found"}), 404

@app.route('/api/notes', methods=['PUT'])
def save_notes():
    data = request.json
    bill_id = data.get('bill_id')
    state = data.get('state')
    notes = data.get('notes', '')

    if not all([bill_id, state]):
        return jsonify({"error": "Missing data"}), 400

    opportunities = load_opportunities()
    for opp in opportunities:
        if opp.get('bill_id') == bill_id and opp.get('state') == state:
            opp['notes'] = notes
            save_opportunities(opportunities)
            return jsonify({"success": True})

    return jsonify({"error": "Opportunity not found"}), 404

if __name__ == '__main__':
    print("Starting Web UI on http://localhost:5001")
    app.run(port=5001, debug=True)
