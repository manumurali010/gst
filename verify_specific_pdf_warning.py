
from src.services.file_validation_service import FileValidationService

file_path = "GSTR3B_32AADFW8764E1Z1_042022.pdf"
case_gstin = "32AADFW8764E1Z1" # Matching GSTIN
case_fy_old = "2022-23" # Matching FY
case_fy_new = "2024-25" # Mismatching FY

print(f"--- Verification for {file_path} ---")

# Test 1: Matching FY (Should Scan Success)
print(f"\n[Test 1] Case FY: {case_fy_old} (Match)")
res, level, payload = FileValidationService.validate_file(file_path, "gstr3b", case_gstin, case_fy_old)
print(f"Result: {res}, Level: {level}")

# Test 2: Mismatching FY (Should Warn)
print(f"\n[Test 2] Case FY: {case_fy_new} (Mismatch)")
res, level, payload = FileValidationService.validate_file(file_path, "gstr3b", case_gstin, case_fy_new)
print(f"Result: {res}, Level: {level}")
if level == "WARNING":
    print(f"Warning Payload: {payload}")
else:
    print("FAILURE: Expected WARNING for FY Mismatch.")
