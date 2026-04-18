from app.core.parser import parse_message

with open("sample_messages/adt_a01.hl7") as f:
    raw = f.read()

result = parse_message(raw)
print("Message type:", result["message_type"])
print("Trigger event:", result["trigger_event"])
print("Sending app:", result["sending_app"])
print("Control ID:", result["message_control_id"])
print("Patient:", result["patient"])
print("Segments found:", result["segment_names"])