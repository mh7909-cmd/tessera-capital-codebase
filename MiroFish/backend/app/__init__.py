"""
MiroFish Backend - Flask Application Factory
"""

import os
import warnings

# Suppress resource_tracker warnings from 3rd-party libraries
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request
from flask_cors import CORS

from .config import Config
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Flask application factory implementation"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Configure JSON serialization parameters
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False
    
    # Initialize high-fidelity logging system
    logger = setup_logger('mirofish')
    
    # Selective logging for primary reloader process
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process
    
    if should_log_startup:
        logger.info("=" * 50)
        logger.info("MiroFish Backend Starting...")
        logger.info("==================================================")
        
        # Register cleanup handlers (ensures simulation processes are terminated on shutdown)
        from app.services.simulation_runner import SimulationRunner
        SimulationRunner.register_cleanup()
        logger.info("Registered simulation cleanup handlers.")
        
        logger.info("MiroFish Backend Initialized.")
    
    # Enable Cross-Origin Resource Sharing (CORS)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Diagnostic request/response middleware
    @app.before_request
    def log_request():
        logger = get_logger('mirofish.request')
        logger.debug(f"Request: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            logger.debug(f"Payload: {request.get_json(silent=True)}")
    
    @app.after_request
    def log_response(response):
        logger = get_logger('mirofish.request')
        logger.debug(f"Response: {response.status_code}")
        return response
    
    # Register core service blueprints
    from .api import graph_bp, simulation_bp, report_bp
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')
    
    # System health verification endpoint
    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'MiroFish Backend'}
    
    if should_log_startup:
        logger.info("MiroFish Backend Ready.")
    
    return app
