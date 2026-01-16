
def format_indian_number(value, prefix_rs=False):
    """
    Formats a number into Indian Numbering System string.
    Rounds to nearest integer. No decimals.
    
    Args:
        value: int, float, or numeric string.
        prefix_rs: If True, adds 'Rs. ' prefix.
        
    Returns:
        str: Formatted string (e.g., "1,23,456", "Rs. 1,000", "0", "Rs. 0").
    """
    try:
        if value is None or value == "":
            num = 0
        else:
            num = float(value)
    except (ValueError, TypeError):
        return str(value) # Return as-is if not numeric

    # Round to nearest integer
    num = int(round(num))
    
    # Handle absolute value for formatting
    is_negative = num < 0
    s_num = str(abs(num))
    
    if len(s_num) <= 3:
        formatted_num = s_num
    else:
        # Last 3 digits
        last_3 = s_num[-3:]
        # Remaining digits
        rest = s_num[:-3]
        # Insert commas every 2 digits from right
        # Reverse, chunk by 2, join, reverse back
        rest_reversed = rest[::-1]
        chunks = [rest_reversed[i:i+2] for i in range(0, len(rest_reversed), 2)]
        rest_formatted = ",".join(chunks)[::-1]
        formatted_num = f"{rest_formatted},{last_3}"
        
    if is_negative:
        formatted_num = "-" + formatted_num
        
    if prefix_rs:
        return f"Rs. {formatted_num}"
    
    return formatted_num
