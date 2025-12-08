import json
import traceback

class LogicValidator:
    @staticmethod
    def validate_logic(logic_code, test_inputs):
        """
        Validates the calculation logic by executing it with test inputs.
        logic_code: str (Python code defining a 'compute' function)
        test_inputs: dict (Input variables)
        Returns: (bool, result_or_error_message)
        """
        try:
            # Create a restricted local scope
            local_scope = {}
            
            # Execute the code definition
            exec(logic_code, {}, local_scope)
            
            # Check if 'compute' function exists
            if 'compute' not in local_scope:
                return False, "Code must define a 'compute(v)' function."
                
            compute_func = local_scope['compute']
            
            # Run the function with test inputs
            result = compute_func(test_inputs)
            
            # Validate result is a dict (JSON object)
            if not isinstance(result, dict):
                return False, f"Function returned {type(result)}, expected dict."
                
            return True, result
            
        except Exception as e:
            return False, f"Execution Error: {str(e)}\n{traceback.format_exc()}"

    @staticmethod
    def get_default_logic_template():
        return """def compute(v):
    # v is a dictionary of input values (placeholders)
    # Example:
    # value = float(v.get('taxable_value', 0))
    # rate = float(v.get('tax_rate', 18))
    # tax = value * (rate / 100)
    
    return {
        "calculated_tax": 0,
        "calculated_interest": 0,
        "calculated_penalty": 0
    }
"""
