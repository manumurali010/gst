# Fix Applied: Conditional Text Now Working

## Problem
The conditional text (AdviceText) and other placeholders were not appearing in the generated DRC-01A document.

## Root Cause
The template (`drc_01a.html`) had all the placeholders correctly defined, but the Python code (`adjudication_wizard.py`) was **missing the replacement logic** for several placeholders:

- `{{CaseID}}`
- `{{FinancialYear}}`
- `{{TradeName}}`
- `{{FormType}}`
- `{{SectionsViolated}}`

## Solution Applied
Added the missing placeholder replacements in `src/ui/adjudication_wizard.py` at lines 397-408:

```python
# Additional Placeholders
html = html.replace("{{CaseID}}", self.current_case_id or "")
html = html.replace("{{FinancialYear}}", self.fy_combo.currentText())
html = html.replace("{{TradeName}}", self.trade_name_input.text() or "")
html = html.replace("{{FormType}}", self.form_combo.currentText())

# Sections Violated (from checkboxes)
violated_sections = []
for cb in self.provision_checks:
    if cb.isChecked():
        violated_sections.append(cb.text())
sections_text = "<br>".join(violated_sections) if violated_sections else "(No sections selected)"
html = html.replace("{{SectionsViolated}}", sections_text)
```

## What Now Works

✅ **Conditional Text (AdviceText)** - Automatically changes based on Section 73 vs 74  
✅ **Case ID** - Displays the current case ID  
✅ **Financial Year** - Shows the selected financial year  
✅ **Trade Name** - Shows the taxpayer's trade name  
✅ **Form Type** - Shows the selected form type  
✅ **Sections Violated** - Lists all checked provisions from the checkboxes  

## Testing
Please test by:
1. Opening the Adjudication Wizard
2. Filling in all fields
3. Selecting Section 73(5) or Section 74(5)
4. Generating a preview or PDF
5. Verify that the conditional text appears correctly at the bottom of the document

The conditional text should now appear as:
- **Section 73**: "You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest in full by {date}, failing which Show Cause Notice will be issued under section 73(1)."
- **Section 74**: "You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest and penalty under section 74(5) by {date}, failing which Show Cause Notice will be issued under section 74(1)."
