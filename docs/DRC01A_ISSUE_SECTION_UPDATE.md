# DRC-01A Template Update - Issue Section & Conditional Advice Text

## Summary

Successfully updated the DRC-01A template and backend logic to include:

1. ✅ **Issue Section** - Added after "Sections Violated" to display the issue description
2. ✅ **Conditional Advice Text** - Automatically changes based on Section 73 or 74
3. ✅ **Last Date for Payment Integration** - Uses the date from the date picker in the advice text

---

## Changes Made

### 1. Template: `templates/drc_01a.html`

#### Added Issue Section (Lines 138-142)
```html
<div class="section-title">Issue:</div>
<div>
    {{IssueDescription}}
</div>
```

This section appears after "Sections Violated" and displays the issue/subject of the case.

#### Conditional Advice Text (Line 145)
The `{{AdviceText}}` placeholder is now populated dynamically based on the section:

**Section 73:**
> "You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest in full by {last_date_payment}, failing which Show Cause Notice will be issued under section 73(1)."

**Section 74:**
> "You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest and penalty under section 74(5) by {last_date_payment}, failing which Show Cause Notice will be issued under section 74(1)."

---

### 2. Backend: `src/ui/proceedings_workspace.py`

#### Updated `generate_drc01a_html()` Method (Lines 618-635)

Added logic to:

1. **Get Last Date for Payment** from the date picker:
```python
last_date_payment = self.payment_date.date().toString("dd/MM/yyyy")
html = html.replace("{{LastDateForPayment}}", last_date_payment)
```

2. **Get Last Date for Reply** from the date picker:
```python
last_date_reply = self.reply_date.date().toString("dd/MM/yyyy")
html = html.replace("{{LastDateForReply}}", last_date_reply)
```

3. **Generate Conditional Advice Text** based on section:
```python
section = self.proceeding_data.get('initiating_section', '')
if "73" in section:
    advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest in full by {last_date_payment}, failing which Show Cause Notice will be issued under section 73(1)."
elif "74" in section:
    advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest and penalty under section 74(5) by {last_date_payment}, failing which Show Cause Notice will be issued under section 74(1)."
else:
    advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest by {last_date_payment}, failing which Show Cause Notice will be issued."

html = html.replace("{{AdviceText}}", advice_text)
```

---

## How It Works

### Flow:

1. **User creates a case** with Initiating Section (73 or 74)
2. **User opens DRC-01A tab** in proceedings workspace
3. **User sets dates**:
   - Last Date for Reply: e.g., 15/01/2025
   - Last Date for Payment: e.g., 15/01/2025
4. **User fills in Issue** in the "Issues Involved" text editor
5. **Preview automatically updates** showing:
   - Issue section with the entered text
   - Conditional advice text with the correct section reference and payment date

### Example Output:

**For Section 73 case with payment date 15/01/2025:**
> You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest in full by 15/01/2025, failing which Show Cause Notice will be issued under section 73(1).

**For Section 74 case with payment date 15/01/2025:**
> You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest and penalty under section 74(5) by 15/01/2025, failing which Show Cause Notice will be issued under section 74(1).

---

## Files Modified

1. [`templates/drc_01a.html`](file:///c:/Users/manum/.gemini/antigravity/scratch/GST_Adjudication_System/templates/drc_01a.html) - Added Issue section and AdviceText placeholder
2. [`src/ui/proceedings_workspace.py`](file:///c:/Users/manum/.gemini/antigravity/scratch/GST_Adjudication_System/src/ui/proceedings_workspace.py) - Added conditional advice text generation logic

---

## Testing

To test:
1. Run the application
2. Create or open a proceeding with Section 73 or 74
3. Navigate to DRC-01A tab
4. Set "Last Date for Payment" to a specific date
5. Enter issue description in "Issues Involved"
6. Check the preview - verify the advice text shows the correct section and date
7. Change the case section and verify the advice text updates accordingly
