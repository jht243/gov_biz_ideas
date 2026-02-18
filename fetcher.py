import os
import datetime
import time
import requests

class LawFetcher:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('OPENSTATES_API_KEY')
        self.base_url = "https://v3.openstates.org/bills"
        
    def fetch_new_bills(self, state=None, since_date=None, limit=100, mock=False):
        """
        Fetches new bills from OpenStates API v3 or returns mock data.
        """
        if mock:
            return self._get_mock_data()

        if not self.api_key:
            print("Warning: No API Key provided. Returning mock data.")
            return self._get_mock_data()

        if not since_date:
            yesterday = datetime.date.today() - datetime.timedelta(days=7)
            since_date = yesterday.strftime('%Y-%m-%d')

        try:
            # OpenStates v3 API params
            # Documentation: https://openstates.github.io/api-manual/v3/bills
            params = {
                'sort': 'updated_desc',
                'per_page': limit,
                'apikey': self.api_key,
                'updated_since': since_date,
                'include': ['abstracts', 'actions']
            }
            if state:
                params['jurisdiction'] = state.upper() 
            
            # Use requests directly instead of broken pyopenstates wrapper
            headers = {"X-API-KEY": self.api_key}
            
            # Simple rate limiting to avoid 429 errors
            time.sleep(7)  # Rate limit: 10 req/min
            
            response = requests.get(self.base_url, params=params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            # The v3 API returns a robust structure. We need to normalize it to our simple dict format.
            # Response format: { "results": [ ... ], "pagination": { ... } }
            
            bills = []
            for item in data.get('results', []):
                # Try to find a longer description from abstracts
                description = item.get('title')
                abstracts = item.get('abstracts', [])
                if abstracts:
                    # Use the first abstract found
                    found_abstract = abstracts[0].get('abstract')
                    if found_abstract:
                        description = found_abstract

                # Formatting: Ensure descriptions look like multiple sentences and respect limits
                if description:
                    # 1. Normalize separators (replace semicolons with periods)
                    if '; ' in description:
                        description = description.replace('; ', '. ')
                    
                    # 2. Split into sentences
                    # Simple split by period, but keep the period attached or re-add it
                    raw_sentences = description.split('. ')
                    clean_sentences = []
                    for s in raw_sentences:
                        s = s.strip()
                        if not s:
                            continue
                        # Capitalize first letter
                        s = s[0].upper() + s[1:]
                        # Add period if missing (and if it's not the last valid chunk which might be concatenated later)
                        if not s.endswith('.'):
                            s += '.'
                        clean_sentences.append(s)
                    
                    # 3. Enforce constraints
                    # Max 5 sentences
                    if len(clean_sentences) > 5:
                        clean_sentences = clean_sentences[:5]
                    
                    # Min 3 sentences (Best Attempt)
                    # We cannot invent text, but if we have fewer than 3, we simply show what we have.
                    # (User request "minimum of 3" is interpreted as "show at least 3 if available, otherwise all")

                    # 4. Insert double newlines for logical segments (Readability Improvement)
                    segmented_description = []
                    for i, s in enumerate(clean_sentences):
                        # Detect natural paragraph transitions in legislative text
                        if i > 0 and (
                            s.startswith("Under existing law") or 
                            s.startswith("This bill") or 
                            s.startswith("The California Constitution") or
                            s.startswith("By imposing new duties")
                        ):
                            segmented_description.append("\n\n" + s)
                        else:
                            segmented_description.append(s)
                    
                    description = ' '.join(segmented_description).replace(' \n\n', '\n\n')

                # Extract dates — prefer latest_action_date, fall back to first_action_date, then created_at
                bill_date = (
                    item.get('latest_action_date') or
                    item.get('first_action_date') or
                    (item.get('created_at', '')[:10] if item.get('created_at') else 'N/A')
                )

                # --- Bill Lifecycle Status ---
                # Derive from action classifications and latest_passage_date
                bill_status = 'Pending'  # default
                latest_passage_date = item.get('latest_passage_date', '')
                latest_action_desc = item.get('latest_action_description', '')
                actions = item.get('actions', [])
                
                # Sort actions by order to process chronologically
                sorted_actions = sorted(actions, key=lambda a: a.get('order', 0))
                
                # Check action classifications for lifecycle events
                for action in sorted_actions:
                    classifications = action.get('classification', [])
                    desc_lower = action.get('description', '').lower()
                    if 'passage' in classifications:
                        bill_status = 'Passed'
                    elif 'executive-signature' in classifications:
                        bill_status = 'Signed into Law'
                    elif 'became-law' in classifications:
                        bill_status = 'Enacted'
                    elif 'executive-veto' in classifications:
                        bill_status = 'Vetoed'
                    elif 'failure' in classifications:
                        bill_status = 'Failed'
                    elif 'withdrawal' in classifications:
                        bill_status = 'Withdrawn'
                
                # Also check latest_passage_date as a fallback signal
                if latest_passage_date and bill_status == 'Pending':
                    bill_status = 'Passed'

                bill = {
                    'id': item.get('identifier'),
                    'title': item.get('title'),
                    'description': description, 
                    'state': item.get('jurisdiction', {}).get('name', 'Unknown'), 
                    'session': item.get('session'),
                    'date': bill_date,
                    'updated_at': item.get('updated_at'),
                    'sources': item.get('openstates_url'),
                    'bill_status': bill_status,
                    'latest_action': latest_action_desc,
                    'latest_action_date': item.get('latest_action_date', ''),
                }
                # Normalize sources to list of dicts for compatibility
                if isinstance(bill['sources'], str):
                    bill['sources'] = [{'url': bill['sources']}]
                
                bills.append(bill)
            
            return bills

        except Exception as e:
            print(f"Error fetching bills: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return []

    def _get_mock_data(self):
        """Returns sample bill data for testing."""
        today = datetime.date.today().isoformat()
        return [
            {
                'id': 'SB 101',
                'title': 'An Act regarding Artificial Intelligence safety',
                'description': 'Establishes a committee to oversee AI development in the state.',
                'state': 'ca',
                'session': '2023-2024',
                'date': today,
                'updated_at': datetime.datetime.now().isoformat(),
                'sources': [{'url': 'http://example.com/sb101'}]
            },
            {
                'id': 'HB 405',
                'title': 'Crypto-currency Mining Regulations',
                'description': 'Requires renewable energy usage for crypto mining operations.',
                'state': 'ny',
                'session': '2023-2024',
                'date': today,
                'updated_at': datetime.datetime.now().isoformat(),
                'sources': [{'url': 'http://example.com/hb405'}]
            },
            {
                'id': 'AB 22',
                'title': 'Wetlands Preservation Act',
                'description': 'Protects local wetlands from new construction projects.',
                'state': 'fl',
                'session': '2023-2024',
                'date': today,
                'updated_at': datetime.datetime.now().isoformat(),
                'sources': [{'url': 'http://example.com/ab22'}]
            }
        ]

