# src/routes/supervisorroute.py

from flask import Blueprint, request, jsonify
from src.model.supervisor import SupervisorAgent

bp = Blueprint("supervisor", __name__, url_prefix="/api")

# Singleton SupervisorAgent instance (optional: move to global state)
supervisor = SupervisorAgent()

@bp.route("/ask-supervisor", methods=["POST"])
def ask_supervisor():
    data = request.get_json()
    task = data.get("task")

    if not task:
        return jsonify({"error": "Missing 'task' in request body"}), 400

    try:
        result = supervisor.delegate(task)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
