def amount_to_words(amount):
    """
    Convert a floating point number to Indian Currency words.
    Example: 125000 -> "Rupees One Lakh Twenty Five Thousand Only"
    """
    if not amount:
        return "Rupees Zero Only"

    def num_to_words_below_1000(n):
        units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
        teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
        
        words = []
        
        if n >= 100:
            words.append(units[n // 100] + " Hundred")
            n %= 100
        
        if n >= 20:
            words.append(tens[n // 10])
            n %= 10
        
        if n >= 10:
            words.append(teens[n - 10])
            n = 0
            
        if n > 0:
            words.append(units[n])
            
        return " ".join(words)

    try:
        amount = float(amount)
        whole_part = int(amount)
        decimal_part = int(round((amount - whole_part) * 100))
        
        words = []
        
        # Crores
        if whole_part >= 10000000:
            crores = whole_part // 10000000
            words.append(num_to_words_below_1000(crores) + " Crore")
            whole_part %= 10000000
            
        # Lakhs
        if whole_part >= 100000:
            lakhs = whole_part // 100000
            words.append(num_to_words_below_1000(lakhs) + " Lakh")
            whole_part %= 100000
            
        # Thousands
        if whole_part >= 1000:
            thousands = whole_part // 1000
            words.append(num_to_words_below_1000(thousands) + " Thousand")
            whole_part %= 1000
            
        if whole_part > 0:
            words.append(num_to_words_below_1000(whole_part))
            
        result = "Rupees " + " ".join(words)
        
        if decimal_part > 0:
            result += " and " + num_to_words_below_1000(decimal_part) + " Paise"
            
        return result + " Only"
        
    except Exception as e:
        return f"Rupees {amount} Only" # Fallback
