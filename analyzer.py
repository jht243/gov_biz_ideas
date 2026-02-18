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
        
        OUR IDEAL CUSTOMER PROFILE — Licensed professionals and small businesses in these categories:
        - Architecture & Interior Design
        - Asbestos Contractors & Consultants
        - Auctioneers
        - Barbers & Cosmetology
        - Building Code Administrators & Inspectors
        - Certified Public Accountants (CPAs)
        - Community Association Managers (HOAs, condos, cooperatives)
        - Construction Industry (general contractors, specialty contractors)
        - Electrical Contractors
        - Engineers
        - Farm Labor contractors
        - Geologists
        - Home Inspectors
        - Landscape Architecture
        - Lodging (hotels, motels, vacation rentals)
        - Mobile Homes (dealers, installers, manufacturers)
        - Mold-Related Services (assessors, remediators)
        - Real Estate (agents, brokers, appraisers)
        - Restaurants & Food Service
        - Talent Agencies & Athlete Agents
        - Timeshare operators
        - Veterinary Medicine
        - Yacht and Ship (dealers, brokers, manufacturers)
        - Drugs, Devices and Cosmetics (pharmacies, small manufacturers)
        - Elevator contractors and inspectors
        - Employee Leasing Companies
        
        These are people who are BUSY running their business, NOT tech-savvy, and will pay for a 
        simple tool that handles compliance for them so they don't get fined.
        
        Bill ID: {bill.get('id')}
        Title: {bill.get('title')}
        State: {bill.get('state')}
        Description: {description}
        
        CRITICAL EXCLUSIONS — Score 0 and set is_opportunity to false for ANY of these:
        - **Government Mandates**: Requirements for state agencies, departments, counties, or municipalities.
        - **Large Institution Mandates**: Requirements for universities, colleges, school districts, hospital systems, or large corporations with their own compliance teams.
        - **B2G (Business to Government)**: We do NOT sell to the government.
        - **Pure Appropriations/Funding**: Bills that just allocate money without a compliance requirement.
        - **Enterprise-Only**: Regulations that only affect companies with >500 employees or corporations.
        - **Internal Government Operations**: Bills about how government agencies should run themselves.

        ═══════════════════════════════════════════════════════
        SCORING RUBRIC — 100 POINTS TOTAL
        Score EACH of the 5 categories independently, then SUM.
        ═══════════════════════════════════════════════════════

        1. TARGET MARKET SIZE (0–25 pts)
           How many small businesses are directly affected by this regulation?
           22-25 = Massive (>100k businesses nationwide in this trade/profession)
           15-21 = Large (25k-100k businesses)
           8-14  = Medium (5k-25k businesses)
           1-7   = Small (<5k businesses)
           0     = No real market / targets government or large corps

        2. EASE OF CLIENT CONVERSION (0–25 pts)
           How easy is it to find, reach, and sell to these business owners?
           22-25 = Can reach via licensing boards, trade associations, or industry lists. Owner is the buyer. No committee approval needed.
           15-21 = Reachable through industry channels. Owner makes buying decisions but may need some convincing.
           8-14  = Harder to identify. May need channel partners or referrals.
           1-7   = Very fragmented, no clear channel. Hard to reach decision-makers.
           0     = Unreachable or buyer is a committee/board.

        3. WILLINGNESS TO PAY (0–20 pts)
           Will these business owners actually spend money on this?
           17-20 = Strong financial pressure — non-compliance means heavy fines ($5k+), license revocation, lawsuits, or loss of insurance. Tool pays for itself 10x.
           11-16 = Moderate pressure — meaningful fines or operational headaches. Clear ROI.
           5-10  = Some pressure — minor fines or inconvenience. ROI is arguable.
           1-4   = Weak pressure — mostly voluntary or one-time hassle.
           0     = No penalty or consequence for non-compliance.

        4. BUILD FEASIBILITY (0–15 pts)
           Can we build this as a simple, standalone SaaS tool?
           13-15 = Pure standalone web app. No integrations needed. Forms, tracking, document generation, alerts.
           9-12  = Mostly standalone but needs some data sources or light integrations.
           5-8   = Needs meaningful integrations with existing systems.
           1-4   = Requires deep integration, hardware, or complex infrastructure.
           0     = Not feasible as software.

        5. COMPETITIVE MOAT (0–15 pts)
           Is this a fresh opportunity or is there already a crowded market?
           13-15 = Brand new regulation, no existing tools, first-mover advantage.
           9-12  = Few or no direct competitors. Existing tools don't specifically address this.
           5-8   = Some competitors exist but room for a better/simpler product.
           1-4   = Crowded market with established players.
           0     = Fully commoditized, no differentiation possible.

        MANDATORY GATE: Score 0 total if the target is government, universities, large hospitals, or corporations with >500 employees.

        ANTI-ANCHORING RULES:
        - Do NOT default to 75. That is lazy scoring.
        - A truly excellent opportunity should score 80-95. A good one 65-79. A mediocre one 40-60.
        - Most bills should score BELOW 55 (not an opportunity). Only truly compelling ones score above 60.
        - You MUST calculate each of the 5 sub-scores independently, then SUM them.

        OUTPUT FORMAT (JSON):
        {{
            "is_opportunity": boolean, // True ONLY if total score > 60 AND target is small business
            "score": integer, // MUST equal the SUM of all 5 category scores
            "score_breakdown": {{
                "market_size": integer,       // 0-25
                "conversion_ease": integer,   // 0-25
                "willingness_to_pay": integer, // 0-20
                "build_feasibility": integer,  // 0-15
                "competitive_moat": integer    // 0-15
            }},
            "summary": "One sentence: what tool we'd build and for whom (name the specific profession/trade)",
            "legislation_overview": "2-3 sentences in plain English. First explain what the new regulation requires and who it affects. Then explain the business opportunity — what tool could be built to help small businesses comply, and why they'd pay for it. Write this for a non-technical business reader.",
            "target_market": "Be specific: e.g. 'Independent HVAC contractors in California' not just 'businesses'",
            "problem_solved": "What pain does this solve for the small business owner?",
            "compliance_trigger": "What specific rule requires this?",
            "reasoning": "Start with score breakdown: Market Size: X/25, Conversion Ease: X/25, Willingness to Pay: X/20, Build Feasibility: X/15, Competitive Moat: X/15 = TOTAL/100. Then explain each score in 1-2 sentences."
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
