# src/routes/supervisorroute.py

from flask import Blueprint, request, jsonify
from src.model.supervisor import SupervisorAgent
from src.model.llm_client import LLMClient
import asyncio

bp = Blueprint("supervisor", __name__, url_prefix="/api")
llm = LLMClient()
supervisor = SupervisorAgent(llm)

@bp.route("/ask-supervisor", methods=["POST"])
def ask_supervisor():
    try:
        data = request.get_json() or {}
        task = data.get("task")
        tasks = data.get("tasks", [])
        
        if not task and not tasks:
            return jsonify({"error": "Missing task or tasks"}), 400
            
        # Kör asynkron kod i en event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Om det finns tasks, kombinera dem med " and "
        if tasks:
            task = " and ".join(tasks)
            
        response = loop.run_until_complete(supervisor.handle(task))
        loop.close()
        
        # Kontrollera om svaret är en sträng eller ett dict
        if isinstance(response, dict):
            return jsonify(response)
        else:
            return jsonify({
                "source": "supervisor",
                "content": response
            })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
