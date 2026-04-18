"""
HL7 ACK (Acknowledgement) Generator.

When a system receives an HL7 message, it must respond with an ACK.
The ACK is itself a mini HL7 message with MSH + MSA segments.

MSA.1 codes:
  AA = Application Accept — message processed OK
  AE = Application Error  — message had validation errors, fix and resend
  AR = Application Reject — cannot process (wrong version, wrong receiver)
"""

from datetime import datetime


def build_ack(original: dict, ack_code: str, error_text: str = "") -> str:
    """
    Build an ACK message string for the original message.

    ACK rules:
      - ACK sender becomes original receiver
      - ACK receiver becomes original sender
      - MSH.9 = ACK
      - MSA.2 = original message control ID
    """
    if ack_code not in ("AA", "AE", "AR"):
        raise ValueError(f"Invalid ACK code: {ack_code}")

    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    original_control_id = original.get("message_control_id", "UNKNOWN")

    ack_sending_app = original.get("receiving_app", "INT_ENGINE")
    ack_sending_fac = original.get("receiving_facility", "DEFAULT_FAC")
    ack_receiving_app = original.get("sending_app", "UNKNOWN")
    ack_receiving_fac = original.get("sending_facility", "UNKNOWN")

    msh = (
        f"MSH|^~\\&|{ack_sending_app}|{ack_sending_fac}|"
        f"{ack_receiving_app}|{ack_receiving_fac}|{now}||ACK|"
        f"ACK{now}|P|2.5"
    )

    error_text_clean = error_text.replace("|", " ").replace("^", " ")[:200]
    msa = f"MSA|{ack_code}|{original_control_id}|{error_text_clean}"

    return f"{msh}\r{msa}"


def determine_ack_code(validation_result: dict) -> tuple:
    """
    Decide which ACK to send based on validation result.

    Returns:
        (ack_code, error_summary)
    """
    if validation_result["valid"]:
        return ("AA", "")

    errors = validation_result.get("errors", [])
    error_summary = "; ".join(errors[:3])
    return ("AE", error_summary)