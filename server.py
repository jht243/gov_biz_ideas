from flask import Flask, render_template, jsonify, request
import json
import os
import requests
import base64
from main import generate_opportunity_report

app = Flask(__name__)
DATA_FILE = 'opportunities.json'
REPORT_FILE = 'opportunity_report.md'

def load_opportunities():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def push_to_github(content_str, message):
    token = os.environ.get('GITHUB_PAT')
    repo = os.environ.get('GITHUB_REPO') # e.g. "user/repo"
    branch = os.environ.get('GITHUB_BRANCH', 'main')

    if not token or not repo:
        return False
        
    url = f"https://api.github.com/repos/{repo}/contents/opportunities.json"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Get current file info to get the SHA
    response = requests.get(url, headers=headers, params={"ref": branch})
    sha = None
    if response.status_code == 200:
        sha = response.json().get('sha')
        
    encoded_content = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
    
    data = {
        "message": message,
        "content": encoded_content,
        "branch": branch
    }
    if sha:
        data["sha"] = sha
        
    put_response = requests.put(url, headers=headers, json=data)
    return put_response.status_code in [200, 201]

def save_opportunities(opportunities):
    with open(DATA_FILE, 'w') as f:
        json.dump(opportunities, f, indent=2)
    
    active_opps = [o for o in opportunities if o.get('status') != 'deleted']
    generate_opportunity_report(active_opps, REPORT_FILE)
    
    # Attempt to persist state remotely to avoid Render ephemeral disk loss
    push_to_github(json.dumps(opportunities, indent=2), "Auto-save UI interactions")

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
    port = int(os.environ.get('PORT', 5001))
    print(f"Starting Web UI on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
