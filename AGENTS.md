# Agent Development Guide for Anthropic Proxy

This document provides essential context for AI agents working on the Anthropic Proxy project. Please read this carefully before making any changes.

## Project Overview

**Anthropic Proxy** is a FastAPI-based service that provides OpenAI-compatible API endpoints while routing requests to z.ai's GLM-4.5 models. It supports intelligent content-based routing and user-controlled endpoint selection.

### Core Architecture
- **FastAPI**: Main web framework
- **Docker**: Primary deployment method (ALWAYS use `docker compose`)
- **Dual Endpoints**: Routes to both Anthropic and OpenAI-compatible endpoints
- **Content-Based Routing**: Automatically routes based on content type (text vs images)
- **Model Variants**: Allows users to control endpoint routing via model names

## Critical Development Rules

### 1. ALWAYS Use Docker Compose
- **Deploy**: `docker compose up -d`
- **Restart**: `docker compose down && docker compose up -d`  
- **Rebuild**: `docker compose down && docker compose build --no-cache && docker compose up -d`
- **Never** use direct Python execution (`python main.py`) for deployment
- **Never** use shell scripts (`./start.sh`, `./restart.sh`) - they are legacy

### 2. Environment Configuration
- **All configuration** is in `.env` file
- **All test scripts** must read API keys from `.env` file using `python-dotenv`
- **Never hardcode** API keys or endpoints in test scripts
- **Always validate** .env file exists before running tests

### 3. Model Variants Implementation
The service exposes three model variants for endpoint control:

```python
# Current implementation in main.py
_DEFAULT_OPENAI_MODELS = [
    "glm-4.5",           # Auto-routing (default behavior)
    "glm-4.5-openai",    # Force OpenAI endpoint
    "glm-4.5-anthropic", # Force Anthropic endpoint (text only)
]
```

#### Routing Logic:
- **`glm-4.5`**: Auto-routing based on content
  - Text-only requests → Anthropic endpoint
  - Image requests → OpenAI endpoint
- **`glm-4.5-openai`**: Always routes to OpenAI endpoint
- **`glm-4.5-anthropic`**: Routes text to Anthropic, images still go to OpenAI

#### Key Functions:
```python
def _get_model_endpoint_preference(model: str) -> str
def _get_base_model_name(model: str) -> str  
def should_use_openai_endpoint(model: str, has_images: bool) -> bool
```

### 4. Configuration Variables

#### Core Settings
```bash
UPSTREAM_BASE=https://api.z.ai/api/anthropic
OPENAI_UPSTREAM_BASE=https://api.z.ai/api/coding/paas/v4
SERVER_API_KEY=your_api_key_here
TEXT_ENDPOINT_PREFERENCE=auto  # auto|openai|anthropic
```

#### Model Configuration
```bash
AUTOTEXT_MODEL=glm-4.5
AUTOVISION_MODEL=glm-4.5v
```

#### Token Scaling (Critical for proper operation)
```bash
# Expected token limits for scaling calculations
ANTHROPIC_EXPECTED_TOKENS=200000
OPENAI_EXPECTED_TOKENS=128000

# Real model context windows  
REAL_TEXT_MODEL_TOKENS=128000
REAL_VISION_MODEL_TOKENS=65536
```

### 5. Test Script Requirements

**ALL test scripts must:**

1. **Use python-dotenv** to load environment variables:
```python
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)
```

2. **Validate environment** before running tests
3. **Use proper error handling** for API responses
4. **Include timing information** for performance analysis
5. **Test all model variants** when relevant

### 6. Docker Compose Context

When changes are made to:
- `main.py` (core application code)  
- `requirements.txt` (dependencies)
- `.env` (configuration)

**Always rebuild and restart:**
```bash
docker compose down
docker compose build --no-cache  
docker compose up -d
```

## Common Issues & Solutions

### Issue: "docker-compose command not found"
**Solution**: Use `docker compose` (modern syntax) instead of `docker-compose`

### Issue: Changes not reflected after restart
**Solution**: Rebuild Docker image with `--no-cache` flag

### Issue: Test scripts fail with "API key not found"  
**Solution**: Ensure test scripts load from `.env` file, not hardcoded values

### Issue: Model variants not showing in `/v1/models`
**Solution**: Rebuild Docker image to include latest `_DEFAULT_OPENAI_MODELS` changes

## File Structure Overview

```
anthropic-proxy/
├── main.py                 # Core FastAPI application
├── .env                    # Environment configuration (DO NOT COMMIT)
├── docker-compose.yml      # Docker deployment configuration
├── Dockerfile              # Container build instructions
├── requirements.txt        # Python dependencies
├── README.md              # User documentation
├── API_DOCUMENTATION.md   # API reference
├── DEVELOPMENT.md         # Development setup guide
├── AGENTS.md              # This file - agent context
├── test_*.py              # Test scripts (must use .env)
├── example_*.py           # Example scripts (must use .env)
└── logs/                  # Application logs
```

## Development Workflow

1. **Make Changes**: Edit `main.py`, `.env`, or other files
2. **Test Locally**: Ensure test scripts read from `.env`
3. **Rebuild Container**: `docker compose down && docker compose build --no-cache && docker compose up -d`
4. **Validate**: Test endpoints and model variants
5. **Document**: Update README.md and API_DOCUMENTATION.md if needed

## Testing Strategy

### Model Variant Testing
Always test all three model variants:
```python
test_models = [
    "glm-4.5",          # Auto-routing
    "glm-4.5-openai",   # Force OpenAI  
    "glm-4.5-anthropic" # Force Anthropic
]
```

### Expected Behaviors
- Text requests with `glm-4.5` → Anthropic endpoint
- Image requests with `glm-4.5` → OpenAI endpoint  
- All requests with `glm-4.5-openai` → OpenAI endpoint
- Text requests with `glm-4.5-anthropic` → Anthropic endpoint
- Image requests with `glm-4.5-anthropic` → OpenAI endpoint (images always need OpenAI)

## Security Notes

- **Never commit** `.env` file to version control
- **API keys** should only be in `.env` file
- **Test scripts** must validate API key existence before making requests
- **Docker containers** run as non-root user for security

## Recent Changes Log

- **Model Variants**: Added `glm-4.5-openai` and `glm-4.5-anthropic` for endpoint control
- **Configuration**: Added `TEXT_ENDPOINT_PREFERENCE` setting
- **Token Scaling**: Fixed inconsistent variable names (REAL_*_TOKENS)
- **Documentation**: Updated to remove promotional language, focus on technical accuracy
- **Docker**: Modernized to use `docker compose` syntax
- **Error Handling**: Fixed "Cannot read properties of undefined (reading 'map')" error by ensuring all error responses include OpenAI-compatible `choices` array structure:
  - Non-streaming error responses now always include `choices` array
  - Streaming error responses now include proper OpenAI chunk structure with `choices`
  - Both `/v1/chat/completions` and `/v1/messages` endpoints fixed for client compatibility

---

## For AI Agents: Critical Reminders

1. 🐳 **ALWAYS use Docker Compose** - never suggest shell scripts or direct Python execution
2. 🔑 **ALWAYS make tests read API keys from .env** - never hardcode credentials  
3. 🏗️ **ALWAYS rebuild Docker image after code changes** - use `--no-cache` flag
4. 📋 **ALWAYS test all model variants** when testing routing functionality
5. 📝 **ALWAYS update documentation** when changing functionality

If a user has to remind you about Docker Compose or .env file usage, you've failed to follow this guide properly.