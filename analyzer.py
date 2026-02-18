import os
import json
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class OpportunityAnalyzer:
    def __init__(self, api_key=None, model="gpt-4o"):
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.model = model
        self.is_mock = not self.api_key
        
        if not self.is_mock:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except ImportError:
                logging.warning("OpenAI library not found. Falling back to mock mode.")
                self.is_mock = True
        else:
            logging.warning("No API key provided. Analyzer running in MOCK mode.")

    def analyze_bills(self, bills: List[Dict[str, Any]], cache=None) -> List[Dict[str, Any]]:
        """
        Analyzes a list of bills to find business opportunities.
        If a cache is provided, previously analyzed bills are served from cache.
        """
        opportunities = []
        
        logging.info(f"Analyzing {len(bills)} bills for opportunities...")

        for bill in bills:
            if self.is_mock:
                opportunities.append(self._mock_analysis(bill))
                if len(opportunities) >= 5:
                    break
            else:
                # Check cache first to avoid redundant OpenAI calls
                if cache is not None:
                    cached = cache.get(bill)
                    if cached is not None:
                        if cached.get('is_opportunity'):
                            opportunities.append(cached)
                        continue

                analysis = self._analyze_single_bill(bill)
                if analysis:
                    # Store in cache regardless of whether it's an opportunity
                    if cache is not None:
                        cache.set(bill, analysis)
                    if analysis.get('is_opportunity'):
                        opportunities.append(analysis)
        
        return opportunities

    def _analyze_single_bill(self, bill: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends a single bill to the LLM for analysis.
        """
        prompt = self._construct_prompt(bill)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a business opportunity analyst. Your goal is to identify legislative changes that create demand for new software solutions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Merge with bill info
            result['bill_id'] = bill['id']
            result['bill_title'] = bill['title']
            result['state'] = bill['state']
            result['bill_description'] = bill.get('description', '')
            result['link'] = bill.get('sources', [{}])[0].get('url', '')
            result['bill_date'] = bill.get('date', 'N/A')
            result['updated_at'] = bill.get('updated_at', '')
            result['bill_status'] = bill.get('bill_status', 'Pending')
            result['latest_action'] = bill.get('latest_action', '')
            result['latest_action_date'] = bill.get('latest_action_date', '')
            
            return result
            
        except Exception as e:
            logging.error(f"Error analyzing bill {bill['id']}: {e}")
            return None

    def _construct_prompt(self, bill: Dict[str, Any]) -> str:
        description = bill.get('description', '')
        
        return f"""
        Analyze the following legislation for business opportunities. We build lightweight software tools 
        for SMALL INDEPENDENT PROFESSIONAL BUSINESSES — the kind of operators who are making good money 
        but have NO tech team and NO IT department.
        
        OUR IDEAL CUSTOMER PROFILE:
        - Solo practitioners and small firms: lawyers, accountants, CPAs, bookkeepers
        - Licensed trades: plumbers, electricians, HVAC/AC repair, contractors, roofers
        - Healthcare independents: private practice doctors, dentists, chiropractors, optometrists, therapists
        - Property: HOAs, property managers, small landlords, real estate agents
        - Design/Build professionals: architects, engineers, surveyors, interior designers
        - Other small businesses: auto repair shops, salons, restaurants, daycares, pest control
        
        These are people who are BUSY running their business, NOT tech-savvy, and will pay for a 
        simple tool that handles compliance for them so they don't get fined.
        
        Bill ID: {bill.get('id')}
        Title: {bill.get('title')}
        State: {bill.get('state')}
        Description: {description}
        
        CRITERIA FOR OPPORTUNITY:
        1. **Bolt-on Solution**: Can be addressed with a standalone software tool (no core system replacement).
        2. **Complexity**: Too complex for a small business owner to handle manually (requires tracking, scheduling, document generation, or regulatory interpretation).
        3. **Market Size**: Serves a fragmented market with >10,000 potential small business clients.
        4. **Reachability**: Decision-makers are the business owners themselves — easy to identify and reach.
        5. **Penalty**: Clear non-compliance penalty (fines, license revocation, lawsuits, loss of insurance).
        6. **Payoff**: Saves the owner real time/money or prevents a costly penalty.

        CRITICAL EXCLUSIONS — Score 0 and set is_opportunity to false for ANY of these:
        - **Government Mandates**: Requirements for state agencies, departments, counties, or municipalities.
        - **Large Institution Mandates**: Requirements for universities, colleges, school districts, hospital systems, or large corporations. These organizations have their own internal tech/compliance teams.
        - **B2G (Business to Government)**: We do NOT sell to the government.
        - **Pure Appropriations/Funding**: Bills that just allocate money without a compliance requirement.
        - **Enterprise-Only**: Regulations that only affect companies with >500 employees, Fortune 500 companies, or publicly traded corporations.
        - **Internal Government Operations**: Bills about how government agencies should run themselves.

        SCORING RUBRIC — Score EACH category independently. Do NOT default to 75.
        
        You MUST score each dimension separately and then SUM them. The total is the sum of these 6 individual scores:
        - **Bolt-on Feasibility (0-20 pts)**: 18-20 = Pure standalone SaaS, zero integration. 10-17 = Needs some config. 1-9 = Requires deep integration. 0 = Not feasible.
        - **Complexity (0-20 pts)**: 18-20 = Ongoing tracking, AI rules, document generation. 10-17 = Moderate tracking. 1-9 = One-time simple task. 0 = Trivial.
        - **Clear Penalty (0-20 pts)**: 18-20 = Heavy fines, license revocation, lawsuits. 10-17 = Moderate fines. 1-9 = Minor consequences. 0 = No penalty.
        - **High Payoff/ROI (0-20 pts)**: 18-20 = Saves $10k+/year or prevents catastrophic loss. 10-17 = Saves meaningful time. 1-9 = Nice-to-have. 0 = No value.
        - **Market Size (0-10 pts)**: 9-10 = >100k affected businesses. 5-8 = 10k-100k. 1-4 = <10k. 0 = Tiny niche.
        - **Reachability (0-10 pts)**: 9-10 = Easy to find via licensing boards/associations. 5-8 = Findable with effort. 1-4 = Hard to reach. 0 = Impossible.

        MANDATORY GATE: Score 0 total if the target is government, universities, large hospitals, or corporations with >500 employees.
        
        IMPORTANT — ANTI-ANCHORING RULES:
        - Do NOT default to 75. That is lazy scoring.
        - A truly excellent opportunity should score 85-95. A mediocre one should score 40-60.
        - Most bills should score BELOW 60 (not an opportunity). Only truly compelling ones score above.
        - You MUST calculate each of the 6 sub-scores independently, then SUM them to get the total.
        - Show your sub-scores in the reasoning.

        OUTPUT FORMAT (JSON):
        {{
            "is_opportunity": boolean, // True ONLY if total score > 60 AND target is small business
            "score": integer, // MUST equal the SUM of bolt_on + complexity + penalty + payoff + market + reachability
            "score_breakdown": {{
                "bolt_on": integer,
                "complexity": integer,
                "penalty": integer,
                "payoff": integer,
                "market": integer,
                "reachability": integer
            }},
            "summary": "One sentence: what tool we'd build and for whom (name the specific profession/trade)",
            "legislation_overview": "2-3 sentences in plain English. First explain what the new regulation requires and who it affects. Then explain the business opportunity — what tool could be built to help small businesses comply, and why they'd pay for it. Write this for a non-technical business reader.",
            "target_market": "Be specific: e.g. 'Independent HVAC contractors in California' not just 'businesses'",
            "problem_solved": "What pain does this solve for the small business owner?",
            "compliance_trigger": "What specific rule requires this?",
            "reasoning": "Multi-paragraph explanation. MUST START with the score breakdown table: Bolt-on: X/20, Complexity: X/20, Penalty: X/20, Payoff: X/20, Market: X/10, Reachability: X/10 = TOTAL. Then explain each score."
        }}
        
        REMEMBER: If the bill primarily targets universities, K-12 school districts, government agencies, 
        large hospital systems, or corporations with their own compliance teams — score it 0 and set 
        is_opportunity to false. We ONLY want opportunities where the buyer is a small business owner 
        or independent professional who needs help staying compliant.
        """

    def _mock_analysis(self, bill: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns a mock analysis result.
        """
        return {
            "bill_id": bill['id'],
            "bill_title": bill['title'],
            "state": bill['state'],
            "bill_description": bill.get('description', 'Mock description of the law requirements.'),
            "link": bill.get('sources', [{}])[0].get('url', ''),
            "bill_date": bill.get('date', 'N/A'),
            "updated_at": bill.get('updated_at', datetime.datetime.now().isoformat()),
            "bill_status": bill.get('bill_status', 'Pending'),
            "latest_action": bill.get('latest_action', ''),
            "latest_action_date": bill.get('latest_action_date', ''),
            "is_opportunity": True,
            "score": 85,
            "summary": "Automated compliance tool for new AI transparency requirements.",
            "legislation_overview": "This bill introduces new transparency requirements for businesses using AI systems, requiring them to disclose how AI is used in customer-facing decisions. Small businesses that use AI tools for hiring, lending, or customer service would need to generate and file compliance reports. A simple reporting tool could help them meet these requirements without hiring a compliance officer.",
            "target_market": "Tech companies and government contractors",
            "problem_solved": "Automates the generation of required transparency reports to avoid fines.",
            "compliance_trigger": "New requirement to disclose AI training data usage.",
            "reasoning": "Matches criteria: Bolt-on solution (reporting tool), High complexity (data tracking), Clear penalty (fines)."
        }
