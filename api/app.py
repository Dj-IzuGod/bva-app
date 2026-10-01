"""
api/app.py -- Flask application factory for the BVA API.

The API is a thin, read-only layer over the pipeline's report files and
configured dataset image directory. It does not use a database.
"""

from flask import Flask, jsonify
from flask_cors import CORS

from api import config
from api.routes.health import health_bp
from api.routes.images import images_bp
from api.routes.report import report_bp
from api.routes.score import score_bp


def create_app():
    """Build, configure, and return the Flask application."""
    app = Flask("bva-api")

    # Useful for direct local browser/API testing. Vite still proxies /api
    # requests during development.
    CORS(app)

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({
            "error": "not_found",
            "message": "No such API route.",
        }), 404

    @app.errorhandler(500)
    def server_error(_error):  # pragma: no cover
        return jsonify({
            "error": "server_error",
            "message": "Internal API error.",
        }), 500

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(report_bp, url_prefix="/api")
    app.register_blueprint(images_bp, url_prefix="/api")
    app.register_blueprint(score_bp)
    


    @app.route("/")
    def index():
        """Return a small service-discovery response."""
        return jsonify({
            "service": "bva-api",
            "message": "BVA API running.",
            "endpoints": [
                "/api/health",
                "/api/summary",
                "/api/pairs",
                "/api/pairs/<pair_id>",
                "/api/image?path=<image_path>",
                "/api/score",
            ],
        })

    return app


# Supports both `python -m api.app` and Flask's app discovery.
app = create_app()

# Cap upload size for POST /api/score (Flask answers 413 above this).
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=True)