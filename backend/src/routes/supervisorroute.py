# src/routes/supervisorroute.py

from flask import Blueprint, request, jsonify
from src.model.supervisor import SupervisorAgent

bp = Blueprint("supervisor", __name__, url_prefix="/api")
supervisor_agent = SupervisorAgent()  # Se till att agenten initieras korrekt

@bp.route("/ask-supervisor", methods=["POST"])
def ask_supervisor():
    data = request.get_json() or {}
    # Byt här: vi väntar på "task" istället för "content"
    task = data.get("task")
    if not task:
        return jsonify({"error": "Missing task"}), 400

    try:
        result = supervisor_agent.delegate(task)
        return jsonify(result)
    except Exception as e:
        # För att fånga eventuella oväntade fel
        return jsonify({"error": str(e)}), 500
