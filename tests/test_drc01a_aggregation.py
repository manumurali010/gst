import unittest
from decimal import Decimal
import re

class LegalReference:
    def __init__(self, raw_text):
        self.raw = raw_text
        self.type = "Other" # Section, Rule, Notification
        self.major = 0
        self.minor = ""
        self.parse()

    def parse(self):
        # Normalization
        text = self.raw.strip()
        # [FIX] Enhanced normalization to catch more variants and ensure boundary
        text = re.sub(r'^(Sec|sec|S|s|u/s|under\s+section)\.?\s+', 'Section ', text, flags=re.I)
        
        # Section Pattern: Section 7(1)(a)
        sec_match = re.search(r'Section\s+(\d+)(.*)', text, re.I)
        if sec_match:
            self.type = "Section"
            self.major = int(sec_match.group(1))
            self.minor = sec_match.group(2).strip()
            self.canonical = f"Section {self.major}{self.minor}"
            return

        # Rule Pattern: Rule 117
        rule_match = re.search(r'Rule\s+(\d+)(.*)', text, re.I)
        if rule_match:
            self.type = "Rule"
            self.major = int(rule_match.group(1))
            self.minor = rule_match.group(2).strip()
            self.canonical = f"Rule {self.major}{self.minor}"
            return
            
        self.canonical = text

    def __eq__(self, other):
        if not isinstance(other, LegalReference): return False
        return (self.type == other.type and 
                self.major == other.major and 
                self.minor == other.minor and
                (self.type != "Other" or self.canonical == other.canonical))

    def __hash__(self):
        return hash((self.type, self.major, self.minor, self.canonical if self.type == "Other" else None))

    def __lt__(self, other):
        type_priority = {"Section": 0, "Rule": 1, "Other": 2}
        if self.type != other.type:
            return type_priority.get(self.type, 2) < type_priority.get(other.type, 2)
        if self.major != other.major:
            return self.major < other.major
        return self.minor < other.minor

def aggregate_legal(provisions_list):
    """Canonicalize, Deduplicate, and Sort"""
    refs = {} # canonical -> object
    for raw in provisions_list:
        parts = re.split(r'[,;\n]', raw)
        for p in parts:
            if p.strip():
                ref = LegalReference(p)
                # Keep the "nicest" version if duplicates found
                if ref.canonical not in refs:
                    refs[ref.canonical] = ref
                else:
                    # Prefer "Section" over "Sec" in raw if both are in set
                    if "Section" in ref.raw and "Section" not in refs[ref.canonical].raw:
                        refs[ref.canonical] = ref
    
    sorted_objs = sorted(refs.values())
    return [r.raw for r in sorted_objs]

class TestDRC01AAggregation(unittest.TestCase):
    def test_legal_normalization(self):
        inputs = ["Sec 7(1)(a)", "Section 7(1)(a)", "s. 16(2)", "Rule 117"]
        result = aggregate_legal(inputs)
        # Expected: Section 7(1)(a) correctly deduplicated + Rule 117
        self.assertEqual(len(result), 3)
        self.assertIn("Section 7(1)(a)", result[0]) # Normalized version
        
    def test_decimal_summation(self):
        # Simulation of float inaccuracy
        values = ["0.1", "0.2"]
        total = sum(Decimal(v) for v in values)
        self.assertEqual(total, Decimal("0.3"))
        
    def test_act_ordering(self):
        priority = ["IGST", "CGST", "SGST", "Cess"]
        data = {"SGST": 100, "IGST": 500, "CGST": 200}
        ordered = sorted(data.keys(), key=lambda x: priority.index(x) if x in priority else 99)
        self.assertEqual(ordered, ["IGST", "CGST", "SGST"])

if __name__ == "__main__":
    unittest.main()
