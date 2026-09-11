"""
Configuration Management
Uniformly load configuration from the .env file in the project root directory.
"""

import os
from dotenv import load_dotenv

# Load .env file from the project root
# Path: MiroFish/.env (relative to backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # If .env does not exist in root, try loading from environment variables (for production)
    load_dotenv(override=True)


class Config:
    """Flask Configuration Class"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # JSON Configuration - Disable ASCII escape to allow non-ASCII characters directly
    JSON_AS_ASCII = False
    
    # LLM Configuration (Unified OpenAI format)
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
    BEAUTIFIER_API_KEY = os.environ.get('BEAUTIFIER_API_KEY')
    
    # Zep Configuration
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')
    
    # Neo4j Configuration
    GRAPH_DATABASE_TYPE = os.environ.get('GRAPH_DATABASE_TYPE', 'neo4j')
    NEO4J_URI = os.environ.get('NEO4J_URI')
    NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')
    
    # Embedding Configuration
    EMBEDDING_API_KEY = os.environ.get('EMBEDDING_API_KEY', LLM_API_KEY)
    EMBEDDING_BASE_URL = os.environ.get('EMBEDDING_BASE_URL', LLM_BASE_URL)
    EMBEDDING_MODEL_NAME = os.environ.get('EMBEDDING_MODEL_NAME', 'nvidia/llama-3_2-nemoretriever-300m-embed-v1')
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    # Text Processing Configuration
    DEFAULT_CHUNK_SIZE = 500  # Default chunk size
    DEFAULT_CHUNK_OVERLAP = 50  # Default chunk overlap
    
    # OASIS Simulation Configuration
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_MAX_TOTAL_AGENTS = int(os.environ.get('OASIS_MAX_TOTAL_AGENTS', '20'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    
    # OASIS Platform Available Actions Configuration
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]
    
    # Report Agent Configuration
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY is not configured")
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY is not configured")
        if cls.GRAPH_DATABASE_TYPE == 'neo4j':
            if not cls.NEO4J_URI:
                errors.append("NEO4J_URI is not configured")
            if not cls.NEO4J_PASSWORD:
                errors.append("NEO4J_PASSWORD is not configured")
        return errors

