"""
Flask REST API endpoints for the HL7 Integration Engine.
"""

import logging
from flask import Blueprint, request, jsonify

from app.core.parser import parse_message
from app.core.validator import validate_message
from app.core.router import route_message
from app.core.ack import build_ack, determine_ack_code
from app.core.storage import (
    save_message, get_all_messages, get_message_by_id, get_stats
)

bp = Blueprint("api", __name__)
log = logging.getLogger(__name__)


@bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "HL7 Integration Engine",
        "version": "1.0.0",
    })


@bp.route("/api/hl7/parse", methods=["POST"])
def parse_endpoint():
    """Full pipeline: parse -> validate -> route -> store -> return ACK."""
    data = request.get_json(silent=True) or {}
    raw = data.get("message", "")

    if not raw:
        return jsonify({
            "success": False,
            "error": "Request body must contain 'message' field",
        }), 400

    try:
        parsed = parse_message(raw)
    except ValueError as e:
        log.warning("Parse failed: %s", e)
        ack = (
            "MSH|^~\\&|OPTUM_INT_ENGINE|OPTUM|UNKNOWN|UNKNOWN|"
            "00000000000000||ACK|ACK0|P|2.5\rMSA|AR||" + str(e)[:100]
        )
        return jsonify({
            "success": False,
            "error": str(e),
            "ack": ack,
        }), 400

    validation = validate_message(parsed)
    routing = route_message(parsed)
    ack_code, error_summary = determine_ack_code(validation)
    ack = build_ack(parsed, ack_code, error_summary)

    msg_id = save_message(raw, parsed, validation, routing, ack_code)

    return jsonify({
        "success": True,
        "message_id": msg_id,
        "message_type": parsed["message_type"],
        "message_control_id": parsed["message_control_id"],
        "patient": parsed["patient"],
        "validation": validation,
        "routing": routing,
        "ack_code": ack_code,
        "ack_message": ack,
    }), 200


@bp.route("/api/hl7/validate", methods=["POST"])
def validate_endpoint():
    """Validate only — does not store."""
    data = request.get_json(silent=True) or {}
    raw = data.get("message", "")

    if not raw:
        return jsonify({"error": "Missing 'message' field"}), 400

    try:
        parsed = parse_message(raw)
    except ValueError as e:
        return jsonify({"valid": False, "errors": [str(e)]}), 400

    validation = validate_message(parsed)
    return jsonify(validation), 200


@bp.route("/api/hl7/messages", methods=["GET"])
def list_messages():
    limit = int(request.args.get("limit", 50))
    messages = get_all_messages(limit)
    return jsonify({"count": len(messages), "messages": messages}), 200


@bp.route("/api/hl7/messages/<int:msg_id>", methods=["GET"])
def get_message(msg_id):
    msg = get_message_by_id(msg_id)
    if not msg:
        return jsonify({"error": f"Message {msg_id} not found"}), 404
    return jsonify(msg), 200


@bp.route("/api/hl7/stats", methods=["GET"])
def stats():
    return jsonify(get_stats()), 200