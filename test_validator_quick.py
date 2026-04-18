from app.core.parser import parse_message
from app.core.validator import validate_message


print("=== VALID MESSAGE TEST ===")
with open("sample_messages/adt_a01.hl7", "r", encoding="utf-8") as f:
    raw_valid = f.read()

parsed_valid = parse_message(raw_valid)
result_valid = validate_message(parsed_valid)

print("Message type:", result_valid["message_type"])
print("Valid:", result_valid["valid"])
print("Errors:", result_valid["errors"])
print("Warnings:", result_valid["warnings"])


print("\n=== INVALID MESSAGE TEST ===")
with open("sample_messages/adt_a01_invalid.hl7", "r", encoding="utf-8") as f:
    raw_invalid = f.read()

parsed_invalid = parse_message(raw_invalid)
result_invalid = validate_message(parsed_invalid)

print("Message type:", result_invalid["message_type"])
print("Valid:", result_invalid["valid"])
print("Errors:", result_invalid["errors"])
print("Warnings:", result_invalid["warnings"])