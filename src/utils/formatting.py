from src.utils.number_utils import safe_int

def format_indian_number(value, prefix_rs=False, decimals=0):
    """
    Formats a number into Indian Numbering System string.
    
    Args:
        value: int, float, or numeric string.
        prefix_rs: If True, adds 'Rs. ' prefix.
        decimals: Number of decimal places to preserve (default 0).
        
    Returns:
        str: Formatted string (e.g., "1,23,456.00", "Rs. 1,000", "0", "Rs. 0").
    """
    try:
        if value is None: return "0"
        num = float(str(value).replace(',', '').replace('₹', '').replace('Rs.', '').replace('Rs', '').strip())
    except (ValueError, TypeError):
        return str(value)

    is_negative = num < 0
    num = abs(num)
    
    # Round to specified decimals
    num = round(num, decimals)
    
    # Split whole and decimal parts
    if decimals > 0:
        s_base = f"{num:.{decimals}f}"
        whole_part, decimal_part = s_base.split('.')
    else:
        whole_part = str(int(round(num)))
        decimal_part = ""
    
    if len(whole_part) <= 3:
        formatted_whole = whole_part
    else:
        last_3 = whole_part[-3:]
        rest = whole_part[:-3]
        rest_reversed = rest[::-1]
        chunks = [rest_reversed[ii:ii+2] for ii in range(0, len(rest_reversed), 2)]
        rest_formatted = ",".join(chunks)[::-1]
        formatted_whole = f"{rest_formatted},{last_3}"
        
    formatted_num = formatted_whole
    if decimal_part:
        formatted_num += f".{decimal_part}"
        
    if is_negative:
        formatted_num = "-" + formatted_num
        
    if prefix_rs:
        return f"Rs. {formatted_num}"
    
    return formatted_num
