from flask import Flask, render_template, jsonify, request
import json
import os
from supabase import create_client, Client
from main import generate_opportunity_report

app = Flask(__name__)
REPORT_FILE = 'opportunity_report.md'

# Initialize Supabase
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase: Client = None

if supabase_url and supabase_key:
    try:
        supabase = create_client(supabase_url, supabase_key)
        print("Connected to Supabase")
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")

def get_db_opportunities():
    if not supabase:
        print("Supabase client not initialized")
        return []
    try:
        # Fetch all records except those marked deleted
        # Supabase API usually uses .neq('status', 'deleted') but status could be null
        # So it's safer to fetch all and filter, or just fetch standard ones.
        res = supabase.table("opportunities").select("*").execute()
        
        # We need to map the DB structure back to the flat JSON format the UI expects
        formatted_opps = []
        for row in res.data:
            if row.get('status') == 'deleted':
                continue
                
            opp = row.get('bill_data', {})
            opp['status'] = row.get('status')
            opp['seen'] = row.get('seen', False)
            opp['notes'] = row.get('notes', '')
            formatted_opps.append(opp)
            
        return formatted_opps
    except Exception as e:
        print(f"Error reading from Supabase: {e}")
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/opportunities', methods=['GET'])
def get_opportunities():
    active_opps = get_db_opportunities()
    return jsonify(active_opps)

@app.route('/api/mark-seen', methods=['POST'])
def mark_seen():
    """Mark all unseen items as seen directly in the database."""
    if not supabase:
        return jsonify({"error": "No database connection"}), 500
        
    try:
        # Get all unseen items
        res = supabase.table("opportunities").select("id").eq("seen", False).execute()
        if not res.data:
            return jsonify({"marked": 0})
            
        count = len(res.data)
        for item in res.data:
            supabase.table("opportunities").update({"seen": True}).eq("id", item["id"]).execute()
            
        return jsonify({"marked": count})
    except Exception as e:
        print(f"Error marking seen: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/action', methods=['POST'])
def handle_action():
    data = request.json
    bill_id = data.get('bill_id')
    state = data.get('state')
    action = data.get('action') # 'do', 'maybe', 'delete'
    
    if not all([bill_id, state, action]) or not supabase:
        return jsonify({"error": "Missing data or DB connection"}), 400
        
    record_id = f"{bill_id}_{state}".replace(' ', '_')
    
    try:
        supabase.table("opportunities").update({"status": action}).eq("id", record_id).execute()
        
        # Optionally regenerate report if we had a background worker
        # But we'll skip generating flat files in the server right now
        # since we are moving away from local file states.
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error handling action: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/notes', methods=['PUT'])
def save_notes():
    data = request.json
    bill_id = data.get('bill_id')
    state = data.get('state')
    notes = data.get('notes', '')

    if not all([bill_id, state]) or not supabase:
        return jsonify({"error": "Missing data or DB connection"}), 400

    record_id = f"{bill_id}_{state}".replace(' ', '_')
    
    try:
        supabase.table("opportunities").update({"notes": notes}).eq("id", record_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error saving notes: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"Starting Web UI on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
