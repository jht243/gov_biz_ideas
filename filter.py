class BillFilter:
    def __init__(self, keywords=None, exclude_keywords=None):
        self.keywords = [k.lower() for k in (keywords or [])]
        self.exclude_keywords = [k.lower() for k in (exclude_keywords or [])]

    def filter_bills(self, bills):
        """
        Filters a list of bills based on keywords matching title or description.
        """
        filtered = []
        for bill in bills:
            text_content = (bill.get('title', '') + ' ' + bill.get('description', '')).lower()
            
            # Check for exclusion first
            if any(ex in text_content for ex in self.exclude_keywords):
                continue
                
            # Check for inclusion
            if not self.keywords:
                # If no keywords provided, maybe we return all? Or none? 
                # Usually if filter is active, we assume we want matches.
                # If keywords is empty, let's assume pass-through for now 
                # (or the user can configure logic). 
                filtered.append(bill)
            else:
                if any(k in text_content for k in self.keywords):
                    filtered.append(bill)
                    
        return filtered
