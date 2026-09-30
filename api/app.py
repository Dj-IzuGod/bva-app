"""
api/app.py -- Flask application factory for the BVA API.

A thin, read-only API over the pipeline's report files:
  - Phase 1: /api/health (liveness + artifact status)
  - Phase 2 will add /api/summary, /api/pairs, /api/pairs/<id>, /api/image
  - Phase 5 stretch: live scoring that REUSES src.embed (never re-implements)

Run from the repo root with the project venv active:
    python -m api.app
"""

from flask import Flask, jsonify
from flask_cors import CORS

from api import config
from api.routes.health import health_bp


def create_app():
    """Build, configure, and return the Flask app."""
    app = Flask("bva-api")

    # The Vite dev server proxies /api to this app (same-origin), so CORS is
    # not required by the frontend itself -- it just makes direct browser
    # testing of the API easier during development.
    CORS(app)

    # JSON error bodies (not HTML) so the React client can handle failures.
    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "not_found", "message": "No such API route."}), 404

    @app.errorhandler(500)
    def server_error(_error):  # pragma: no cover
        return jsonify({"error": "server_error", "message": "Internal API error."}), 500

    app.register_blueprint(health_bp, url_prefix="/api")

    @app.route("/")
    def index():
        return jsonify({
            "service": "bva-api",
            "message": "BVA API running. Endpoints: /api/health",
        })

    return app


# Module-level app so `flask --app api.app run` also works.
app = create_app()

if __name__ == "__main__":
    # debug=True -> auto-reload on save. Development only.
    app.run(host=config.HOST, port=config.PORT, debug=True)
