import os
from flask import Flask, send_from_directory

def create_app():
    app = Flask(__name__)

    # Register your API routes
    from .routes import status
    app.register_blueprint(status.bp)
    from .routes import supervisorroute
    app.register_blueprint(supervisorroute.bp)

    # Serve React frontend from frontend/dist
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_react(path):
        dist_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
        target = os.path.join(dist_dir, path)

        if path != "" and os.path.exists(target):
            return send_from_directory(dist_dir, path)
        else:
            return send_from_directory(dist_dir, "index.html")

    return app
