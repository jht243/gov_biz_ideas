import os
import json
import datetime
import argparse
from fetcher import LawFetcher
from filter import BillFilter
from analyzer import OpportunityAnalyzer
from cache import BillCache

# Configuration defaults
DEFAULT_KEYWORDS = ["AI", "Artificial Intelligence", "Crypto", "Blockchain", "Privacy", "Environment", "Carbon"]
DEFAULT_STATES = ["CA", "NY", "TX", "FL", "IL", "PA", "NV", "DE", "TN"]

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

    # 1. Fetch
    print("Fetching new bills...")
    all_bills = []
    
    if mock_mode:
         all_bills = fetcher.fetch_new_bills(mock=True)
         print(f"Fetched {len(all_bills)} bills (Mock).")
    else:
        states_to_check = DEFAULT_STATES
        
        for state in states_to_check:
            print(f"  Checking {state}...")
            state_bills = fetcher.fetch_new_bills(state=state, limit=20) 
            print(f"    - Found {len(state_bills)} bills in {state}.")
            all_bills.extend(state_bills)
            
    print(f"Total fetched: {len(all_bills)} bills.")

    # 2. Filter bills
    print(f"Filtering for keywords: {DEFAULT_KEYWORDS}")
    relevant_bills = bill_filter.filter_bills(all_bills)
    print(f"Found {len(relevant_bills)} relevant bills.")

    # 3. Analyze Opportunities (AI Layer) — with cache to avoid re-analyzing
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("Note: OPENAI_API_KEY not found. Running Analyzer in MOCK mode.")
    
    analyzer = OpportunityAnalyzer(api_key=openai_api_key)
    opportunities = analyzer.analyze_bills(relevant_bills, cache=bill_cache)
    
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
        
        json_path = os.path.join(os.getcwd(), 'opportunities.json')
        
        # RULE: User-classified bills are immutable.
        #  - "do" / "maybe" bills are ALWAYS kept, even if pipeline doesn't find them again
        #  - "deleted" bills are NEVER re-added, even if pipeline finds them again
        #  - Only brand-new, unclassified bills from the pipeline get appended
        old_opps = []
        if os.path.exists(json_path):
            try:
                with open(json_path) as f:
                    old_opps = json.load(f)
            except Exception:
                old_opps = []
        
        # Build sets for classified bills
        preserved = {}      # bills with do/maybe — keep exactly as-is
        dismissed = set()    # bills with deleted — never show again
        for old in old_opps:
            key = (old.get('bill_id',''), old.get('state',''))
            status = old.get('status', '')
            if status in ('do', 'maybe'):
                preserved[key] = old
            elif status == 'deleted':
                dismissed.add(key)
        
        # Start with all preserved (do/maybe) bills
        final = list(preserved.values())
        
        # Add new pipeline results — only if not already classified
        for opp in opportunities:
            key = (opp.get('bill_id',''), opp.get('state',''))
            if key in preserved:
                continue   # already keeping the user's version
            if key in dismissed:
                continue   # user said no, don't bring it back
            final.append(opp)
        
        # Also keep deleted entries in the file so we remember the dismissals
        for old in old_opps:
            key = (old.get('bill_id',''), old.get('state',''))
            if old.get('status') == 'deleted':
                final.append(old)
        
        with open(json_path, 'w') as f:
            json.dump(final, f, indent=2)
        print(f"Opportunities JSON saved: {json_path} ({len(preserved)} preserved, {len(dismissed)} dismissed, {len(final) - len(preserved) - len(dismissed)} new)")

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
