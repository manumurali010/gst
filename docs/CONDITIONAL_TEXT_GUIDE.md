# Where to Edit Conditional Text in Backend

## Location: `src/ui/adjudication_wizard.py`

### Function: `generate_drc01a_html()` (Lines 336-495)

The conditional text logic is located in the `generate_drc01a_html()` method. Here's where you can customize it:

## Lines 377-395: Conditional Text Logic

```python
# SCN Section Logic
if "73" in proceeding_section:
    scn_section = "section 73(1)"
    advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest in full by {compliance_date} , failing which Show Cause Notice will be issued under section 73(1)."
elif "74" in proceeding_section:
    scn_section = "section 74(1)"
    advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest and penalty under section 74(5) by {compliance_date} , failing which Show Cause Notice will be issued under section 74(1)."
else:
    scn_section = "section 73(1)/74(1)"
    advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest in full by {compliance_date} , failing which Show Cause Notice will be issued under section 73(1)/74(1)."
```

## How to Edit:

1. **For Section 73 Text**: Edit line 380
2. **For Section 74 Text**: Edit line 383
3. **For Default/Both Sections Text**: Edit line 386

## Variables Available:
- `compliance_date`: The compliance date in dd/MM/yyyy format
- `proceeding_section`: The selected section (e.g., "Section 73(5)")
- `total_tax`, `total_int`, `total_pen`, `total_grand`: Calculated totals

## Example Customization:

```python
# Section 73 - Custom text
advice_text = f"You must pay ₹{total_grand:,.0f} (including tax and interest) by {compliance_date}. Failure to comply will result in issuance of Show Cause Notice under section 73(1) of the CGST Act, 2017."

# Section 74 - Custom text with penalty mention
advice_text = f"You are directed to pay ₹{total_grand:,.0f} (tax: ₹{total_tax:,.0f}, interest: ₹{total_int:,.0f}, penalty: ₹{total_pen:,.0f}) by {compliance_date}. Non-compliance will attract Show Cause Notice under section 74(1) of the CGST Act, 2017."
```

## Template Placeholder:

The generated `advice_text` is inserted into the template using:
```python
html = html.replace("{{AdviceText}}", advice_text)
```

This corresponds to `{{AdviceText}}` in `templates/drc_01a.html` (line 147).
