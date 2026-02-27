import os
import json
import datetime
import argparse
from fetcher import LawFetcher
from filter import BillFilter
from analyzer import OpportunityAnalyzer
from cache import BillCache
from supabase import create_client, Client

# Configuration defaults
DEFAULT_KEYWORDS = ["AI", "Artificial Intelligence", "Crypto", "Blockchain", "Privacy", "Environment", "Carbon"]
DEFAULT_STATES = ["CA", "NY", "TX", "FL", "IL", "PA", "NV", "DE", "TN"]
ALL_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]
STATE_BATCH_SIZE = 5

def run_tracker(mock_mode=False, output_file="todays_report.md"):
    print(f"--- State Law Tracker Job: {datetime.datetime.now()} ---")
    
    # Initialize components
    api_key = os.environ.get("OPENSTATES_API_KEY")
    if not api_key and not mock_mode:
        print("No API Key found. Switching to Mock Mode automatically.")
        mock_mode = True

    fetcher = LawFetcher(api_key=api_key)
    bill_filter = BillFilter(keywords=DEFAULT_KEYWORDS)
    bill_cache = BillCache()

    # Load previously saved opportunities to skip already processed ones
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    supabase: Client = None
    
    old_opps = []
    if supabase_url and supabase_key:
        try:
            supabase = create_client(supabase_url, supabase_key)
            result = supabase.table("opportunities").select("*").execute()
            old_opps = result.data
        except Exception as e:
            print(f"Error connecting to Supabase: {e}")
            old_opps = []
    else:
        print("Warning: SUPABASE_URL or SUPABASE_KEY not found. Data persistence will be disabled unless mocking.")

    preserved = {}       # bills with do/maybe — keep exactly as-is
    dismissed = set()    # bills with deleted — never show again
    seen_ids = set()     # track what we've seen so we don't count it as a "new" email opportunity
    
    for old in old_opps:
        # In Supabase, our ID is "bill_id_state"
        # We need to map back to (bill_id, state) tuple for matching logic
        # OR we can just use the bill_data payload
        payload = old.get('bill_data', {})
        b_id = payload.get('bill_id', '')
        state = payload.get('state', '')
        key = (b_id, state)
        
        status = old.get('status', '')
        if status in ('do', 'maybe'):
            preserved[key] = payload
        elif status == 'deleted':
            dismissed.add(key)
        
        seen_ids.add(key)

    # 0. Initialize analyzer once (shared across all batches)
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("Note: OPENAI_API_KEY not found. Running Analyzer in MOCK mode.")
    analyzer = OpportunityAnalyzer(api_key=openai_api_key)

    # 1. Fetch
    print("Fetching new bills...")
    all_bills = []
    relevant_bills = []
    opportunities = []

    if mock_mode:
        all_bills = fetcher.fetch_new_bills(mock=True)
        print(f"Fetched {len(all_bills)} bills (Mock).")

        print(f"Filtering for keywords: {DEFAULT_KEYWORDS}")
        relevant_bills = bill_filter.filter_bills(all_bills)
        print(f"Found {len(relevant_bills)} relevant bills.")

        opportunities = analyzer.analyze_bills(relevant_bills, cache=bill_cache)
    else:
        states_to_check = DEFAULT_STATES + [s for s in ALL_STATES if s not in DEFAULT_STATES]
        print(f"Will scan up to {len(states_to_check)} states total in batches of {STATE_BATCH_SIZE}.")

        for i in range(0, len(states_to_check), STATE_BATCH_SIZE):
            batch = states_to_check[i:i + STATE_BATCH_SIZE]
            batch_number = (i // STATE_BATCH_SIZE) + 1
            print(f"  Batch {batch_number}: {', '.join(batch)}")

            batch_bills = []
            for state in batch:
                print(f"    Checking {state}...")
                state_bills = fetcher.fetch_new_bills(state=state, limit=20)
                print(f"      - Found {len(state_bills)} bills in {state}.")
                batch_bills.extend(state_bills)

            all_bills.extend(batch_bills)

            batch_relevant = bill_filter.filter_bills(batch_bills)
            relevant_bills.extend(batch_relevant)
            print(f"    Relevant bills this batch: {len(batch_relevant)}")

            if not batch_relevant:
                continue

            batch_opportunities = analyzer.analyze_bills(batch_relevant, cache=bill_cache)
            opportunities.extend(batch_opportunities)

            # "Useful for email" = not already tracked in the database
            new_for_email = [
                opp for opp in batch_opportunities
                if (opp.get('bill_id', ''), opp.get('state', '')) not in seen_ids
            ]
            if new_for_email:
                print(
                    f"Found {len(new_for_email)} new email-eligible opportunities. "
                    "Stopping early instead of scanning more states."
                )
                break
        else:
            print("Scanned all 50 states and found no new opportunities for email.")

    print(f"Total fetched: {len(all_bills)} bills.")

    # De-duplicate opportunities by (bill_id, state) while preserving order.
    deduped_opportunities = []
    seen_opp_keys = set()
    for opp in opportunities:
        key = (opp.get('bill_id', ''), opp.get('state', ''))
        if key in seen_opp_keys:
            continue
        seen_opp_keys.add(key)
        deduped_opportunities.append(opp)
    opportunities = deduped_opportunities
    
    # Save cache after analysis
    bill_cache.save()
    print(bill_cache.stats())
    
    print(f"Identified {len(opportunities)} potential business opportunities.")

    # 4. Generate Reports
    report_path = os.path.join(os.getcwd(), 'todays_report.md')
    generate_report(relevant_bills, report_path)
    print(f"Report generated: {report_path}")
    
    if opportunities:
        opportunity_path = os.path.join(os.getcwd(), 'opportunity_report.md')
        generate_opportunity_report(opportunities, opportunity_path)
        print(f"Opportunity Analysis generated: {opportunity_path}")

        new_count = 0
        
        if supabase:
            for opp in opportunities:
                b_id = opp.get('bill_id', '')
                state = opp.get('state', '')
                key = (b_id, state)
                
                if key not in seen_ids:
                    new_count += 1
                    
                # Generate unique ID for Supabase
                record_id = f"{b_id}_{state}".replace(' ', '_')
                
                # We only upsert items that are NOT preserved (do/maybe) or dismissed (deleted)
                # If they are preserved/dismissed, they exist in DB with user state, we don't want to overwrite that
                # We use ON CONFLICT to avoid overwriting user state if it exists
                
                data = {
                    "id": record_id,
                    "bill_data": opp
                }
                
                try:
                    # In Supabase, to ignore conflicts and not override user status,
                    # we do an upsert but rely on DB constraints or we simply insert and ignore errors.
                    # Since python supabase client doesn't have complex ON CONFLICT DO NOTHING natively via easy API,
                    # we check if it's already in our seen_ids (from DB).
                    if key not in seen_ids:
                        supabase.table("opportunities").insert(data).execute()
                    else:
                        # Existing item. We could update bill_data but we don't want to touch status/seen/notes.
                        # For now, let's just skip updating existing records to preserve user state safely.
                        pass
                except Exception as e:
                    print(f"Error saving to database: {e}")

            print(
                f"Opportunities saved to Supabase: "
                f"({len(preserved)} preserved, {len(dismissed)} dismissed, {new_count} new)"
            )
        else:
            print(f"No Supabase connection. Found {new_count} new opportunities but could not save them.")

def generate_opportunity_report(opportunities, filepath):
    with open(filepath, 'w') as f:
        f.write(f"# High-Value Business Opportunities: {datetime.date.today()}\n\n")
        f.write(f"Total Opportunities Identified: {len(opportunities)}\n\n")
        
        for opp in opportunities:
            f.write(f"## [{opp['score']}/100] {opp['summary']}\n")
            f.write(f"**Target Market**: {opp['target_market']}\n\n")
            f.write(f"**Problem**: {opp['problem_solved']}\n\n")
            f.write(f"**Trigger**: {opp['compliance_trigger']}\n\n")
            f.write(f"**Why it fits**: {opp['reasoning']}\n\n")
            bill_date = opp.get('bill_date', 'N/A')
            f.write(f"**Source Bill**: [{opp['state']} {opp['bill_id']}]({opp['link']}) - {opp['bill_title']} (Date: {bill_date})\n")
            f.write("---\n")

def generate_report(bills, filepath):
    with open(filepath, 'w') as f:
        f.write(f"# Daily Legislative Report: {datetime.date.today()}\n\n")
        f.write(f"Total Matches: {len(bills)}\n\n")
        for bill in bills:
            title = bill.get('title', 'No Title')
            desc = bill.get('description', 'No Description')
            state = bill.get('state', 'Unknown State').upper()
            bid = bill.get('id', 'N/A')
            sources = bill.get('sources', [])
            url = sources[0]['url'] if sources else '#'
            
            f.write(f"## [{state}] {bid}: {title}\n")
            f.write(f"**Description**: {desc}\n\n")
            bill_date = bill.get('date', 'N/A')
            f.write(f"**Bill Date**: {bill_date}\n\n")
            f.write(f"[Link to Bill]({url})\n")
            f.write("---\n")
    
    print(f"Report generated: {filepath}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="State Law Tracker")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode with sample data")
    args = parser.parse_args()
    
    # Output to the same directory for now
    output_path = os.path.join(os.path.dirname(__file__), "todays_report.md")
    
    run_tracker(mock_mode=args.mock, output_file=output_path)
