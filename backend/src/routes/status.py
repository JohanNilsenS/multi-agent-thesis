# src/routes/status.py
from flask import Blueprint, jsonify

bp = Blueprint('status', __name__, url_prefix='/status')

@bp.route('/', methods=['GET'])
def get_status():
    return jsonify({"status": "ok"})
