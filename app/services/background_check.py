from typing import Dict
import random

class BackgroundChecker:
    def __init__(self):
        # Mock database of records
        self.records = {
            "John": {"status": "flagged", "details": "Court record found in Bangalore"},
            "Alice": {"status": "clear", "details": "No records found"},
            "Bob": {"status": "flagged", "details": "Employment verification pending"},
        }

    def check(self, name: str, location: str) -> Dict:
        """Perform a background check on a candidate."""
        # In a real implementation, this would call an external API
        # For now, we'll use our mock database
        
        # Check if we have a record for this name
        if name in self.records:
            return self.records[name]
        
        # For names not in our database, randomly generate a result
        # In a real implementation, this would be replaced with actual API calls
        status = random.choice(["clear", "flagged"])
        if status == "clear":
            return {
                "status": "clear",
                "details": f"No records found in {location}"
            }
        else:
            return {
                "status": "flagged",
                "details": f"Verification required for {location}"
            }

    def add_record(self, name: str, status: str, details: str):
        """Add a record to the mock database."""
        self.records[name] = {
            "status": status,
            "details": details
        } 