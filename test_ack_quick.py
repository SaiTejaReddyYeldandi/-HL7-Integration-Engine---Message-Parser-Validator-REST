from app.core.parser import parse_message
from app.core.validator import validate_message
from app.core.ack import build_ack, determine_ack_code


print("=== VALID MESSAGE ACK ===")
with open("sample_messages/adt_a01.hl7", "r", encoding="utf-8") as f:
    raw_valid = f.read()

parsed_valid = parse_message(raw_valid)
validation_valid = validate_message(parsed_valid)
ack_code_valid, error_text_valid = determine_ack_code(validation_valid)
ack_valid = build_ack(parsed_valid, ack_code_valid, error_text_valid)

print("ACK code:", ack_code_valid)
print(ack_valid.replace("\r", "\n"))


print("\n=== INVALID MESSAGE ACK ===")
with open("sample_messages/adt_a01_invalid.hl7", "r", encoding="utf-8") as f:
    raw_invalid = f.read()

parsed_invalid = parse_message(raw_invalid)
validation_invalid = validate_message(parsed_invalid)
ack_code_invalid, error_text_invalid = determine_ack_code(validation_invalid)
ack_invalid = build_ack(parsed_invalid, ack_code_invalid, error_text_invalid)

print("ACK code:", ack_code_invalid)
print(ack_invalid.replace("\r", "\n"))