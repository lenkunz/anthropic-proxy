
# file: anthro_mapper_proxy.py
# OpenAI↔Anthropic proxy for Roo Code & friends.
# - Anthropic: /v1/messages, /v1/messages/count_tokens
# - OpenAI compat: /v1/chat/completions, /v1/models
# - Robust OAI→Anthropic mapping (images, system), SSE bridge, logs, stacktraces
# - Vision-aware count scaling

import os
import re
import json
import time
import math
import uuid
import base64
import asyncio
import hashlib
import traceback
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request, Response, HTTPException
from starlette.responses import StreamingResponse, JSONResponse
import httpx
from httpx_sse import aconnect_sse, SSEError
from dotenv import load_dotenv

try:
    import tiktoken
except Exception:
    tiktoken = None

load_dotenv()
app = FastAPI()

# ---------------------- Config ----------------------
MODEL_MAP = json.loads(os.getenv("MODEL_MAP_JSON", "{}"))
UPSTREAM_BASE = os.getenv("UPSTREAM_BASE", "https://api.z.ai/api/anthropic")
OPENAI_UPSTREAM_BASE = os.getenv("OPENAI_UPSTREAM_BASE", "https://api.z.ai/api/paas/v4")
SERVER_API_KEY = os.getenv("SERVER_API_KEY", "")
FORWARD_CLIENT_KEY = os.getenv("FORWARD_CLIENT_KEY", "true").lower() in ("1", "true", "yes")
FORWARD_COUNT_TO_UPSTREAM = os.getenv("FORWARD_COUNT_TO_UPSTREAM", "true").lower() in ("1", "true", "yes")
FORCE_ANTHROPIC_BETA = os.getenv("FORCE_ANTHROPIC_BETA", "false").lower() in ("1", "true", "yes")
DEFAULT_ANTHROPIC_BETA = os.getenv("DEFAULT_ANTHROPIC_BETA", "prompt-caching-2024-07-31")

AUTOTEXT_MODEL = os.getenv("AUTOTEXT_MODEL", "glm-4.5")
AUTOVISION_MODEL = os.getenv("AUTOVISION_MODEL", "glm-4.5v")

_DEFAULT_OPENAI_MODELS = [
    "glm-4.5",
]

def _load_openai_models() -> List[str]:
    raw = os.getenv("OPENAI_MODELS_LIST_JSON")
    if not raw:
        return list(_DEFAULT_OPENAI_MODELS)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
            return parsed
    except Exception:
        pass
    return list(_DEFAULT_OPENAI_MODELS)

OPENAI_MODELS_LIST = _load_openai_models()

COUNT_SHAPE_COMPAT = os.getenv("COUNT_SHAPE_COMPAT", "true").lower() in ("1", "true", "yes")

# Token scaling configuration
SCALE_COUNT_TOKENS_FOR_VISION = os.getenv("SCALE_COUNT_TOKENS_FOR_VISION", "true").lower() in ("1", "true", "yes")
TEXT_WINDOW = int(os.getenv("TEXT_WINDOW", "229376"))
VISION_WINDOW = int(os.getenv("VISION_WINDOW", "229376")) 
VISION_COUNT_SCALE = float(os.getenv("VISION_COUNT_SCALE", "0.0"))

# Token scaling for different endpoints and models
# Context window sizes for different model types and endpoints
ANTHROPIC_TEXT_WINDOW = 200000      # Anthropic text models (scaled up)
OPENAI_TEXT_WINDOW = 131072         # OpenAI text models (128k)
OPENAI_VISION_WINDOW = 65535        # OpenAI vision models (64k)

# Scaling factors
ANTHROPIC_TO_OPENAI_TEXT_SCALE = OPENAI_TEXT_WINDOW / ANTHROPIC_TEXT_WINDOW    # 131072 / 200000 ≈ 0.656
OPENAI_TO_ANTHROPIC_TEXT_SCALE = ANTHROPIC_TEXT_WINDOW / OPENAI_TEXT_WINDOW    # 200000 / 131072 ≈ 1.526
OPENAI_TEXT_TO_VISION_SCALE = OPENAI_VISION_WINDOW / OPENAI_TEXT_WINDOW        # 65535 / 131072 ≈ 0.500
OPENAI_VISION_TO_TEXT_SCALE = OPENAI_TEXT_WINDOW / OPENAI_VISION_WINDOW        # 131072 / 65535 ≈ 2.000
ANTHROPIC_TO_OPENAI_VISION_SCALE = OPENAI_VISION_WINDOW / ANTHROPIC_TEXT_WINDOW # 65535 / 200000 ≈ 0.328

# Retry configuration
RETRY_BACKOFF = float(os.getenv("RETRY_BACKOFF", "0.1"))  # Start with faster retries

# Connection timeout configuration
STREAM_TIMEOUT = float(os.getenv("STREAM_TIMEOUT", "300.0"))  # 5 minutes for streaming connections
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "120.0"))  # 2 minutes for regular requests
CONNECT_TIMEOUT = float(os.getenv("CONNECT_TIMEOUT", "10.0"))   # 10 seconds to establish connection

# Debug flag for optional verbose logging
DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")

# ---------------------- Logging ----------------------
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
MAX_STRING_IN_LOG = 200

try:
    encoding = tiktoken.encoding_for_model("gpt-4")
except Exception:
    encoding = None

def _encoding():
    if tiktoken is None:
        return None
    try:
        return tiktoken.encoding_for_model("gpt-4")
    except Exception:
        return tiktoken.get_encoding("cl100k_base")

def _trim_strings(obj: Any, limit: int = MAX_STRING_IN_LOG) -> Any:
    if isinstance(obj, str) and len(obj) > limit:
        return obj[:limit] + "...[truncated]"
    elif isinstance(obj, dict):
        return {k: _trim_strings(v, limit) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_trim_strings(v, limit) for v in obj]
    return obj

def _write_log(kind: str, endpoint: str, req_id: str, payload: Any):
    try:
        return tiktoken.encoding_for_model("gpt-4o")
    except Exception:
        try:
            return tiktoken.get_encoding("cl100k_base")
        except Exception:
            return None
ENCODING = _encoding()

# ---------------------- Logging & traces ----------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S.%fZ")

def _trim_strings(obj: Any, limit: int = MAX_STRING_IN_LOG) -> Any:
    if limit and limit > 0:
        if isinstance(obj, str):
            return obj if len(obj) <= limit else obj[:limit] + f"... [TRIMMED {len(obj)-limit} chars]"
        if isinstance(obj, list):
            return [_trim_strings(x, limit) for x in obj]
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                if str(k).lower() in ("authorization", "x-api-key", "api-key"):
                    out[k] = "[REDACTED]"
                else:
                    out[k] = _trim_strings(v, limit)
            return out
    return obj

def _write_log(kind: str, endpoint: str, req_id: str, payload: Any):
    fname = f"{_now_iso()}_{endpoint}_{kind}_{req_id}.json"
    fpath = LOG_DIR / fname
    try:
        with fpath.open("w", encoding="utf-8") as f:
            json.dump(_trim_strings(payload), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] failed to write log {fpath}: {e}")

def _resp_body_as_obj(r: httpx.Response):
    try:
        return r.json()
    except Exception:
        try:
            return r.text
        except Exception:
            return f"<{len(r.content)} bytes>"

def _payload_digest(payload: Any) -> str:
    try:
        s = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    except Exception:
        s = str(payload)
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()

def _exc_info(exc: BaseException) -> Dict[str, Any]:
    try:
        tb = traceback.TracebackException.from_exception(exc)
        return {"type": exc.__class__.__name__, "message": str(exc), "stack": "".join(tb.format())}
    except Exception:
        return {"type": exc.__class__.__name__, "message": str(exc), "stack": traceback.format_exc()}

@app.middleware("http")
async def log_exceptions_middleware(request: Request, call_next):
    req_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    try:
        return await call_next(request)
    except Exception as e:
        _write_log("err", "middleware", req_id, {"path": str(request.url), "method": request.method, "exc": _exc_info(e)})
        return JSONResponse(status_code=500, content={"detail": "internal server error", "proxy_error_id": req_id})

# ---------------------- HTTP retry helper ----------------------
class ConnectionLostError(Exception):
    """Raised when upstream connection is lost and should propagate to client."""
    pass

async def _post_with_retries(client: httpx.AsyncClient, url: str, *, json: Any, headers: Dict[str, str], tries: int = 3, backoff: float = None) -> httpx.Response:
    if backoff is None:
        backoff = RETRY_BACKOFF
    last_exc = None
    for i in range(tries):
        try:
            # DEBUG: Log headers before request to identify None values
            if DEBUG:
                print(f"[DEBUG] _post_with_retries headers (attempt {i+1}): {headers}")
                none_headers = {k: v for k, v in headers.items() if v is None}
                if none_headers:
                    print(f"[DEBUG] _post_with_retries found None headers: {none_headers}")
            r = await client.post(url, json=json, headers=headers)
            r.raise_for_status()  # raise to log stack on 4xx/5xx
            return r
        except httpx.HTTPStatusError as e:
            _write_log("upstream_err", "generic_post", "retry", {
                "try": i + 1,
                "status": e.response.status_code if e.response else None,
                "headers": dict(e.response.headers) if e.response else None,
                "body": _resp_body_as_obj(e.response) if e.response else None,
                "upstream_url": str(e.request.url) if e.request else url,
                "exc": _exc_info(e),
            })
            # retry on 5xx only
            if e.response is not None and e.response.status_code >= 500:
                if i < tries - 1:  # Don't sleep on the last attempt
                    await asyncio.sleep(backoff * (2 ** i))
                continue
            raise
        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as e:
            last_exc = e
            _write_log("upstream_err", "generic_post", "retry", {
                "try": i + 1, "exception": str(e), "exc": _exc_info(e), "upstream_url": url
            })
            # For connection errors, don't retry on the last attempt
            if i < tries - 1:
                await asyncio.sleep(backoff * (2 ** i))
            continue
        except httpx.HTTPError as e:
            last_exc = e
            _write_log("upstream_err", "generic_post", "retry", {
                "try": i + 1, "exception": str(e), "exc": _exc_info(e), "upstream_url": url
            })
            if i < tries - 1:
                await asyncio.sleep(backoff * (2 ** i))
    
    # If we exhausted retries, raise a ConnectionLostError to propagate to client
    if last_exc:
        if isinstance(last_exc, (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError)):
            raise ConnectionLostError(f"Upstream connection failed: {last_exc}") from last_exc
        raise last_exc
    raise RuntimeError("Retries exhausted")

# ---------------------- Token helpers ----------------------
def count_tokens_from_messages(messages):
    if ENCODING is None:
        def approx(s: str) -> int: return max(1, len(s.encode("utf-8")) // 4)
    else:
        def approx(s: str) -> int: return len(ENCODING.encode(s))
    if not isinstance(messages, list): return approx(str(messages))
    s = []
    for m in messages:
        role = m.get("role", "")
        content = m.get("content", "")
        s.append(f"<{role}>: {content}")
    return approx("\n".join(s))

def payload_has_cache_control(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "cache_control": return True
            if isinstance(v, (dict, list)) and payload_has_cache_control(v): return True
    elif isinstance(obj, list):
        for item in obj:
            if payload_has_cache_control(item): return True
    return False

def normalize_messages(input_messages):
    if input_messages is None: return []
    if isinstance(input_messages, str): return [{"role": "user", "content": input_messages}]
    if not isinstance(input_messages, list): return []
    out = []
    for item in input_messages:
        if not isinstance(item, dict):
            out.append({"role":"user","content":str(item)}); continue
        if "role" in item and "content" in item:
            out.append({"role":item["role"],"content":item["content"]}); continue
        if "text" in item and "type" in item:
            typ = item.get("type"); role = "user"
            if typ in ("assistant","system"): role = typ
            out.append({"role": role, "content": item.get("text","")}); continue
        if "content" in item:
            out.append({"role":"user","content":item["content"]}); continue
        if "message" in item:
            out.append({"role":"user","content":item["message"]}); continue
        out.append({"role":"user","content":json.dumps(item)})
    return out

def payload_metadata(payload):
    try:
        s = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        b = s.encode("utf-8"); return len(b), hashlib.sha256(b).hexdigest()
    except Exception:
        try:
            txt = str(payload); b = txt.encode("utf-8", errors="ignore")
            return len(b), hashlib.sha256(b).hexdigest()
        except Exception:
            return None, None

def extract_usage_from_message_obj(msg_obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(msg_obj, dict): return None
    usage = msg_obj.get("usage")
    if isinstance(usage, dict): return usage
    for k, v in msg_obj.items():
        if isinstance(v, dict) and "input_tokens" in v: return v
    return None

def deep_search_for_usage(obj: Any) -> Optional[Dict[str, Any]]:
    if isinstance(obj, dict):
        if "usage" in obj and isinstance(obj["usage"], dict): return obj["usage"]
        if "input_tokens" in obj and isinstance(obj.get("input_tokens"), (int, float)):
            return {k: obj[k] for k in obj.keys() if k in ("input_tokens","output_tokens","cache_creation_input_tokens","cache_read_input_tokens")}
        for k, v in obj.items():
            if isinstance(v, dict) and "input_tokens" in v:
                return {k2: v.get(k2) for k2 in ("input_tokens","output_tokens","cache_creation_input_tokens","cache_read_input_tokens") if k2 in v}
    elif isinstance(obj, list):
        for item in obj[:10]:
            if isinstance(item, (dict, list)):
                found = deep_search_for_usage(item)
                if found: return found
    return None

def parse_sse_bytes_for_usage(content_bytes: bytes) -> Optional[Dict[str, Any]]:
    try:
        text = content_bytes.decode("utf-8", errors="ignore")
        frames = text.split("\n\n")
        for frame in frames:
            data_lines = [ln[len("data:"):].strip() for ln in frame.splitlines() if ln.strip().startswith("data:")]
            if not data_lines: continue
            try:
                parsed = json.loads("\n".join(data_lines))
            except Exception:
                parsed = None
            if parsed:
                found = deep_search_for_usage(parsed)
                if found: return found
    except Exception:
        return None
    return None

# ---------------------- Image detection ----------------------
def content_block_has_image(cb: Any) -> bool:
    if not isinstance(cb, dict): return False
    t = cb.get("type")
    if t == "image" and isinstance(cb.get("source"), dict): return True
    if t in ("input_image", "image_url") and (cb.get("source") or cb.get("url") or cb.get("image_url")): return True
    if t == "image" and isinstance(cb.get("image"), (dict, str)): return True
    return False

def message_has_image(msg: Dict[str, Any]) -> bool:
    if not isinstance(msg, dict): return False
    c = msg.get("content")
    if isinstance(c, list): return any(content_block_has_image(b) for b in c if isinstance(b, dict))
    if isinstance(c, dict) and content_block_has_image(c): return True
    return False

def payload_has_image(payload: Dict[str, Any]) -> bool:
    if not isinstance(payload, dict): return False
    msgs = payload.get("messages")
    if isinstance(msgs, list) and any(message_has_image(m) for m in msgs if isinstance(m, dict)): return True
    atts = payload.get("attachments")
    if isinstance(atts, list):
        for a in atts:
            if isinstance(a, dict) and a.get("type") in ("image","input_image","image_url"): return True
    return False

def should_use_openai_endpoint(model: Optional[str], has_images: bool) -> bool:
    """Determine if request should be routed to OpenAI-compatible endpoint."""
    # Route to OpenAI endpoint if:
    # 1. Model is the vision model (AUTOVISION_MODEL) 
    # 2. Request contains images (regardless of model)
    if model == AUTOVISION_MODEL or has_images:
        return True
    return False

def convert_openai_to_simple_format(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Convert OpenAI image_url format to simple format expected by upstream."""
    converted = payload.copy()
    
    if "messages" in converted:
        new_messages = []
        for msg in converted["messages"]:
            if not isinstance(msg, dict):
                new_messages.append(msg)
                continue
            
            content = msg.get("content")
            if isinstance(content, list):
                # Convert from OpenAI format [{"type": "text", "text": "..."}, {"type": "image_url", "image_url": {"url": "..."}}]
                # to simple format: "text content data:image/png;base64,..."
                text_parts = []
                image_parts = []
                
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "image_url":
                            image_url = block.get("image_url", {})
                            if isinstance(image_url, dict):
                                url = image_url.get("url", "")
                                if url:
                                    image_parts.append(url)
                
                # Combine text and images into simple format
                combined_content = " ".join(text_parts)
                if image_parts:
                    combined_content = f"{combined_content} {' '.join(image_parts)}".strip()
                
                new_msg = msg.copy()
                new_msg["content"] = combined_content
                new_messages.append(new_msg)
            else:
                new_messages.append(msg)
        
        converted["messages"] = new_messages
    
    return converted

# ---------------------- Usage helpers ----------------------
def _as_int_or_none(value: Any) -> Optional[int]:
    """Convert a value to a non-negative integer or None if invalid."""
    if isinstance(value, bool):
        # Booleans should not be converted to integers in token usage
        return None
    if isinstance(value, (int, float)):
        try:
            result = int(value)
            return result if result >= 0 else None
        except (ValueError, OverflowError):
            return None
    if isinstance(value, str):
        try:
            result = int(float(value))
            return result if result >= 0 else None
        except (ValueError, OverflowError):
            return None
    return None

def convert_usage_to_openai(usage: Optional[Dict[str, Any]]) -> Dict[str, Optional[int]]:
    """Convert Anthropic usage format to OpenAI format.
    
    Anthropic format:
    {
        "input_tokens": 123,
        "output_tokens": 456,
        "cache_creation_input_tokens": 10,  # optional
        "cache_read_input_tokens": 5       # optional
    }
    
    OpenAI format:
    {
        "prompt_tokens": 138,  # input + cache tokens
        "completion_tokens": 456,
        "total_tokens": 594
    }
    """
    if not isinstance(usage, dict):
        return {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}

    # Handle prompt tokens (input + cache tokens)
    prompt = _as_int_or_none(usage.get("prompt_tokens"))
    if prompt is None:
        # Start with base input tokens
        base_input = _as_int_or_none(usage.get("input_tokens")) or 0
        
        # Add cache-related tokens to input
        cache_creation = _as_int_or_none(usage.get("cache_creation_input_tokens")) or 0
        cache_read = _as_int_or_none(usage.get("cache_read_input_tokens")) or 0
        
        # Sum all input-related tokens
        if base_input > 0 or cache_creation > 0 or cache_read > 0:
            prompt = base_input + cache_creation + cache_read
        else:
            prompt = None

    # Handle completion tokens
    completion = _as_int_or_none(usage.get("completion_tokens"))
    if completion is None:
        completion = _as_int_or_none(usage.get("output_tokens"))

    # Handle total tokens
    total = _as_int_or_none(usage.get("total_tokens"))
    if total is None:
        # Try combined_tokens first as a fallback
        total = _as_int_or_none(usage.get("combined_tokens"))
    
    # If still no total and we have both prompt and completion, calculate it
    if total is None and prompt is not None and completion is not None:
        total = prompt + completion

    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
    }

# ---------------------- Upstream helpers ----------------------
async def upstream_count_tokens(client: httpx.AsyncClient, headers: Dict[str, str], body: Dict[str, Any]) -> Optional[int]:
    url = UPSTREAM_BASE.rstrip("/") + "/v1/messages/count_tokens"
    try:
        rr = await client.post(url, json=body, headers=headers, timeout=120.0)
        if rr.status_code >= 400: return None
        j = rr.json()
        for k in ("input_tokens","token_count","input_token_count","count"):
            if isinstance(j, dict) and isinstance(j.get(k), (int, float)): return int(j[k])
    except Exception:
        return None
    return None

# ---------------------- Count shape & scaling ----------------------
def unify_count_tokens_shape(parsed: Optional[Dict[str, Any]], fallback_tokens: Optional[int]) -> Dict[str, Any]:
    result = parsed.copy() if isinstance(parsed, dict) else {}
    val = None
    for k in ("input_tokens","token_count","input_token_count","count"):
        if isinstance(parsed, dict) and k in parsed and isinstance(parsed[k], (int, float)):
            val = int(parsed[k]); break
    if val is None and isinstance(fallback_tokens, int):
        val = int(fallback_tokens); result["proxy_estimate"] = True
    if val is None:
        val = 0; result["proxy_estimate"] = True
    result["input_tokens"] = val
    result["token_count"] = val
    result["input_token_count"] = val
    return result

def _vision_effective_scale() -> float:
    return 1.0

def _maybe_scale_count_for_vision(val: int, routed_model: Optional[str], img_present: bool) -> int:
    """Scale token counts for vision requests based on configuration."""
    if not SCALE_COUNT_TOKENS_FOR_VISION: 
        return int(val or 0)
    
    vision_active = bool(img_present) or (routed_model == AUTOVISION_MODEL)
    if not vision_active: 
        return int(val or 0)
    
    scale = _vision_effective_scale()
    return max(0, int(math.ceil((val or 0) * scale)))

def _scale_tokens_for_openai_response(tokens: int, upstream_endpoint: str, downstream_endpoint: str, is_vision: bool = False) -> int:
    """Scale tokens based on upstream and downstream endpoint context windows."""
    if tokens is None or tokens <= 0:
        return tokens
    
    scale_factor = 1.0
    
    # Determine scaling based on endpoint combination
    if upstream_endpoint == "anthropic" and downstream_endpoint == "openai":
        if is_vision:
            # Anthropic (200k) -> OpenAI Vision (64k)
            scale_factor = ANTHROPIC_TO_OPENAI_VISION_SCALE
        else:
            # Anthropic (200k) -> OpenAI Text (128k)  
            scale_factor = ANTHROPIC_TO_OPENAI_TEXT_SCALE
    elif upstream_endpoint == "openai" and downstream_endpoint == "anthropic":
        if is_vision:
            # This shouldn't happen (OpenAI vision -> Anthropic), but handle it
            scale_factor = 1.0 / ANTHROPIC_TO_OPENAI_VISION_SCALE
        else:
            # OpenAI (128k) -> Anthropic (200k)
            scale_factor = OPENAI_TO_ANTHROPIC_TEXT_SCALE
    elif upstream_endpoint == "openai" and downstream_endpoint == "openai":
        if is_vision:
            # OpenAI Vision (64k) -> OpenAI Text (128k) - client expects 128k context
            scale_factor = OPENAI_VISION_TO_TEXT_SCALE
        # else: OpenAI Text -> OpenAI Text, no scaling needed
    # else: Anthropic -> Anthropic, no scaling needed
    
    if scale_factor != 1.0:
        scaled = int(tokens * scale_factor)
        return max(1, scaled)  # Ensure at least 1 token
    
    return tokens

def _get_endpoint_type(use_openai_endpoint: bool) -> str:
    """Get endpoint type string for scaling calculations."""
    return "openai" if use_openai_endpoint else "anthropic"

def _is_vision_request(model: Optional[str], has_images: bool) -> bool:
    """Determine if this is a vision request."""
    return has_images or (model == AUTOVISION_MODEL)

def _scale_openai_response_tokens(response_data: Dict[str, Any], upstream_endpoint: str, downstream_endpoint: str, model: Optional[str] = None, has_images: bool = False) -> Dict[str, Any]:
    """Scale token counts in OpenAI response based on endpoint combination."""
    if not isinstance(response_data, dict):
        return response_data
    
    # Make a copy to avoid modifying the original
    scaled_response = response_data.copy()
    
    # Determine if this is a vision request
    is_vision = _is_vision_request(model, has_images)
    
    # Scale usage tokens if present
    if "usage" in scaled_response and isinstance(scaled_response["usage"], dict):
        usage = scaled_response["usage"].copy()
        
        if "prompt_tokens" in usage and usage["prompt_tokens"]:
            usage["prompt_tokens"] = _scale_tokens_for_openai_response(
                usage["prompt_tokens"], upstream_endpoint, downstream_endpoint, is_vision
            )
            
        if "completion_tokens" in usage and usage["completion_tokens"]:
            usage["completion_tokens"] = _scale_tokens_for_openai_response(
                usage["completion_tokens"], upstream_endpoint, downstream_endpoint, is_vision
            )
            
        if "total_tokens" in usage and usage["total_tokens"]:
            usage["total_tokens"] = _scale_tokens_for_openai_response(
                usage["total_tokens"], upstream_endpoint, downstream_endpoint, is_vision
            )
        
        scaled_response["usage"] = usage
    
    return scaled_response

def _scale_openai_streaming_chunk(chunk_data: Dict[str, Any], upstream_endpoint: str, downstream_endpoint: str, model: Optional[str] = None, has_images: bool = False) -> Dict[str, Any]:
    """Scale token counts in OpenAI streaming response chunk."""
    if not isinstance(chunk_data, dict):
        return chunk_data
    
    # Make a copy to avoid modifying the original
    scaled_chunk = chunk_data.copy()
    
    # Determine if this is a vision request
    is_vision = _is_vision_request(model, has_images)
    
    # Scale usage tokens if present in streaming chunk
    if "usage" in scaled_chunk and isinstance(scaled_chunk["usage"], dict):
        usage = scaled_chunk["usage"].copy()
        
        if "prompt_tokens" in usage and usage["prompt_tokens"]:
            usage["prompt_tokens"] = _scale_tokens_for_openai_response(
                usage["prompt_tokens"], upstream_endpoint, downstream_endpoint, is_vision
            )
            
        if "completion_tokens" in usage and usage["completion_tokens"]:
            usage["completion_tokens"] = _scale_tokens_for_openai_response(
                usage["completion_tokens"], upstream_endpoint, downstream_endpoint, is_vision
            )
            
        if "total_tokens" in usage and usage["total_tokens"]:
            usage["total_tokens"] = _scale_tokens_for_openai_response(
                usage["total_tokens"], upstream_endpoint, downstream_endpoint, is_vision
            )
        
        scaled_chunk["usage"] = usage
    
    return scaled_chunk
    """Scale down tokens from Anthropic's 200k context to OpenAI's 128k context."""
    if not is_anthropic_scaled:
        return tokens
    
    # Scale down from Anthropic's inflated context window to OpenAI's original size
    scaled = int(tokens / ANTHROPIC_SCALE_FACTOR)
    return max(1, scaled)  # Ensure at least 1 token

# ---------------------- /v1/messages/count_tokens ----------------------
@app.post("/v1/messages/count_tokens")
async def token_count_forward_or_local(request: Request):
    req_id = uuid.uuid4().hex[:12]
    try:
        payload = await request.json()
    except Exception as e:
        _write_log("err", "count_tokens", req_id, {"where":"parse_json","exc":_exc_info(e)})
        raise HTTPException(status_code=400, detail="invalid json")

    if isinstance(payload, dict):
        if "messages" in payload:
            payload["messages"] = normalize_messages(payload["messages"])
        elif "system" in payload and "messages" not in payload:
            sys_block = payload.get("system")
            if isinstance(sys_block, list): payload["messages"] = normalize_messages(sys_block)
            elif isinstance(sys_block, dict): payload["messages"] = normalize_messages([sys_block])
            elif isinstance(sys_block, str): payload["messages"] = normalize_messages(sys_block)

        incoming_model = payload.get("model")
        img_present = payload_has_image(payload)
        # if not incoming_model:
        payload["model"] = AUTOVISION_MODEL if img_present else AUTOTEXT_MODEL
        _write_log(f"[DEBUG] count_tokens: img_present={img_present}, incoming_model={incoming_model}, set model to {payload['model']}")
        # else:
        #     if img_present and incoming_model == AUTOTEXT_MODEL:
        #         payload["model"] = AUTOVISION_MODEL
        #     elif (not img_present) and incoming_model == AUTOVISION_MODEL:
        #         payload["model"] = AUTOTEXT_MODEL

        if payload.get("model") in MODEL_MAP:
            payload["model"] = MODEL_MAP[payload["model"]]

    size, digest = payload_metadata(payload)
    _write_log("req", "count_tokens", req_id, {"headers": dict(request.headers), "payload": payload, "payload_bytes": size, "payload_sha256": digest})

    if not FORWARD_COUNT_TO_UPSTREAM:
        try:
            if isinstance(payload, dict) and "messages" in payload:
                tokens = count_tokens_from_messages(payload["messages"])
            elif isinstance(payload, dict) and "text" in payload:
                tokens = len((ENCODING.encode(payload["text"]) if ENCODING else payload["text"].encode("utf-8"))) // (1 if ENCODING else 4)
            else:
                s = json.dumps(payload); tokens = len((ENCODING.encode(s) if ENCODING else s.encode("utf-8"))) // (1 if ENCODING else 4)
            body = unify_count_tokens_shape({"input_tokens": tokens}, tokens) if COUNT_SHAPE_COMPAT else {"token_count": tokens}
            routed_model = (payload or {}).get("model"); img_present = payload_has_image(payload)
            eff = _maybe_scale_count_for_vision(int(body.get("input_tokens",0)), routed_model, img_present)
            body["input_tokens"] = body["token_count"] = body["input_token_count"] = eff
            resp = Response(content=json.dumps(body), media_type="application/json")
            if eff != tokens: resp.headers["X-Proxy-Count-Scaled"] = "VISION"
            _write_log("resp","count_tokens",req_id,{"body":body,"scaled":eff!=tokens})
            return resp
        except Exception as e:
            _write_log("err","count_tokens",req_id,{"where":"local_count","exc":_exc_info(e)})
            raise

    headers = {"content-type":"application/json"}
    incoming_ver = request.headers.get("anthropic-version")
    headers["anthropic-version"] = incoming_ver if incoming_ver else "2023-06-01"
    anth_beta = request.headers.get("anthropic-beta")
    if anth_beta: headers["anthropic-beta"] = anth_beta
    if (not anth_beta) and FORCE_ANTHROPIC_BETA and payload_has_cache_control(payload):
        headers["anthropic-beta"] = DEFAULT_ANTHROPIC_BETA

    client_xkey = request.headers.get("x-api-key")
    client_auth = request.headers.get("authorization")
    if FORWARD_CLIENT_KEY and (client_xkey or client_auth):
        if client_xkey:
            headers["x-api-key"] = client_xkey
        elif SERVER_API_KEY:
            headers["x-api-key"] = SERVER_API_KEY
        if client_auth and not client_xkey: headers["authorization"] = client_auth
    else:
        if SERVER_API_KEY: headers["x-api-key"] = SERVER_API_KEY

    upstream_url = UPSTREAM_BASE.rstrip("/") + "/v1/messages/count_tokens"

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # DEBUG: Log headers before request to identify None values
            print(f"[DEBUG] Headers before upstream request: {headers}")
            none_headers = {k: v for k, v in headers.items() if v is None}
            if none_headers:
                print(f"[DEBUG] Found None headers: {none_headers}")
            # Filter out None values from headers to prevent TypeError
            filtered_headers = {k: v for k, v in headers.items() if v is not None}
            r = await client.post(upstream_url, json=payload, headers=filtered_headers)
        except httpx.HTTPError as e:
            _write_log("err","count_tokens",req_id,{"where":"upstream_http","exc":_exc_info(e)})
            local_est = 0
            try:
                if isinstance(payload, dict) and "messages" in payload:
                    local_est = count_tokens_from_messages(payload["messages"])
                else:
                    s = json.dumps(payload); local_est = len((ENCODING.encode(s) if ENCODING else s.encode("utf-8"))) // (1 if ENCODING else 4)
            except Exception as e2:
                _write_log("err","count_tokens",req_id,{"where":"local_est_after_upstream_err","exc":_exc_info(e2)})
            body = unify_count_tokens_shape({}, local_est)
            routed_model = (payload or {}).get("model"); img_present = payload_has_image(payload)
            eff = _maybe_scale_count_for_vision(int(body.get("input_tokens",0)), routed_model, img_present)
            body["input_tokens"] = body["token_count"] = body["input_token_count"] = eff
            resp = Response(content=json.dumps(body), media_type="application/json", status_code=200)
            if eff != int(local_est): resp.headers["X-Proxy-Count-Scaled"] = "VISION"
            _write_log("resp","count_tokens",req_id,{"body":body,"scaled":eff!=int(local_est)})
            return resp

        try:
            parsed = r.json()
        except Exception as e:
            _write_log("err","count_tokens",req_id,{"where":"parse_upstream_json","exc":_exc_info(e)})
            parsed = None

        if r.status_code >= 400:
            local_est = 0
            try:
                if isinstance(payload, dict) and "messages" in payload:
                    local_est = count_tokens_from_messages(payload["messages"])
                else:
                    s = json.dumps(payload); local_est = len((ENCODING.encode(s) if ENCODING else s.encode("utf-8"))) // (1 if ENCODING else 4)
            except Exception as e2:
                _write_log("err","count_tokens",req_id,{"where":"local_est_on_4xx_5xx","exc":_exc_info(e2)})
            body = unify_count_tokens_shape(parsed if isinstance(parsed, dict) else {}, local_est)
            routed_model = (payload or {}).get("model"); img_present = payload_has_image(payload)
            eff = _maybe_scale_count_for_vision(int(body.get("input_tokens",0)), routed_model, img_present)
            body["input_tokens"] = body["token_count"] = body["input_token_count"] = eff
            resp = Response(content=json.dumps(body), media_type="application/json", status_code=200)
            if eff != int(local_est): resp.headers["X-Proxy-Count-Scaled"] = "VISION"
            _write_log("resp","count_tokens",req_id,{"body":body,"scaled":eff!=int(local_est),"upstream_status":r.status_code,"upstream_body":parsed})
            return resp

        body = unify_count_tokens_shape(parsed if isinstance(parsed, dict) else {}, None)
        routed_model = (payload or {}).get("model"); img_present = payload_has_image(payload)
        eff = _maybe_scale_count_for_vision(int(body.get("input_tokens",0)), routed_model, img_present)
        orig = int(parsed.get("input_tokens", 0) if isinstance(parsed, dict) else 0)
        body["input_tokens"] = body["token_count"] = body["input_token_count"] = eff
        resp = Response(content=json.dumps(body), media_type="application/json", status_code=200)
        if eff != orig: resp.headers["X-Proxy-Count-Scaled"] = "VISION"
        _write_log("resp","count_tokens",req_id,{"body":body,"scaled":eff!=orig,"upstream_body":parsed})
        return resp

# ---------------------- OpenAI-compatible /v1/models ----------------------
@app.get("/v1/models")
async def openai_models():
    req_id = uuid.uuid4().hex[:12]
    models = []
    created = int(time.time())
    ids = list(dict.fromkeys(OPENAI_MODELS_LIST + list(MODEL_MAP.keys())))
    for mid in ids:
        models.append({"id": mid, "object": "model", "created": created, "owned_by": "proxy"})
    obj = {"object": "list", "data": models}
    _write_log("resp","models",req_id,obj)
    return Response(content=json.dumps(obj, ensure_ascii=False), media_type="application/json")

@app.get("/v1/models/{model_id}")
async def openai_model_one(model_id: str):
    req_id = uuid.uuid4().hex[:12]
    created = int(time.time())
    ids = set(OPENAI_MODELS_LIST + list(MODEL_MAP.keys()))
    if model_id not in ids:
        _write_log("resp","models",req_id,{"error":"model_not_found","id":model_id})
        raise HTTPException(status_code=404, detail={"error":{"message":"Model not found","type":"invalid_request_error"}})
    obj = {"id": model_id, "object": "model", "created": created, "owned_by": "proxy"}
    _write_log("resp","models",req_id,obj)
    return Response(content=json.dumps(obj, ensure_ascii=False), media_type="application/json")

# ---------------------- OAI→Anthropic mapping (FIXED) ----------------------
_DATA_URL_RE = re.compile(r"^data:(?P<media>[^;,]+)?(?P<b64>;base64)?,(?P<data>.+)$", re.IGNORECASE)

def _parse_data_url(url_str: str) -> Optional[Dict[str, str]]:
    """
    Parse RFC 2397 data: URL.
    Returns {"media_type": "...", "data_b64": "..."} or None if invalid.
    """
    m = _DATA_URL_RE.match(url_str or "")
    if not m: return None
    media = (m.group("media") or "").strip() or "application/octet-stream"
    is_b64 = bool(m.group("b64"))
    data = m.group("data") or ""
    try:
        if is_b64:
            # ensure it's valid base64 (strip any whitespace)
            _ = base64.b64decode(data, validate=True)
            data_b64 = data
        else:
            # percent-decoded raw -> encode to base64
            raw = bytes(data, "utf-8")
            data_b64 = base64.b64encode(raw).decode("ascii")
        return {"media_type": media, "data_b64": data_b64}
    except Exception:
        return None

def _anthropic_image_block_from_oai_part(part: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Accepts an OpenAI image part:
      {"type":"image_url","image_url":"https://..."}
      {"type":"image_url","image_url":{"url":"https://...","detail":"high"}}
      {"type":"image_url","image_url":{"url":"data:image/png;base64,AAA..."}}
    Produces Anthropic block:
      {"type":"image","source":{"type":"url","url":"..."}}
      OR {"type":"image","source":{"type":"base64","media_type":"image/png","data":"AAA..."}}
    Returns None if invalid.
    """
    if not isinstance(part, dict) or part.get("type") != "image_url":
        return None

    src = part.get("image_url")
    url_str: Optional[str] = None
    if isinstance(src, str):
        url_str = src.strip()
    elif isinstance(src, dict):
        val = src.get("url")
        if isinstance(val, str):
            url_str = val.strip()

    if not url_str:
        return None  # invalid; skip

    if url_str.lower().startswith("data:"):
        parsed = _parse_data_url(url_str)
        if not parsed:
            return None
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": parsed["media_type"],
                "data": parsed["data_b64"],
            }
        }

    # basic sanity: must look like a URL
    if not (url_str.startswith("http://") or url_str.startswith("https://")):
        return None

    return {"type": "image", "source": {"type": "url", "url": url_str}}

def _map_openai_messages_to_anthropic(openai_msgs: List[Dict[str, Any]], req_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Robust mapping:
      - Merge all OAI system messages into one Anthropic 'system' (list of text blocks)
      - For user/assistant, produce content blocks (text + image)
      - Validate image parts & data: URLs; drop invalid parts safely
    """
    system_texts: List[str] = []
    new_messages: List[Dict[str, Any]] = []

    for m in openai_msgs or []:
        role = m.get("role")
        content = m.get("content")

        # Collect systems
        if role == "system":
            if isinstance(content, str):
                system_texts.append(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        system_texts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        system_texts.append(part)
            else:
                system_texts.append(str(content))
            continue

        # Map user/assistant messages
        out_msg = {"role": role or "user", "content": []}

        if isinstance(content, str):
            out_msg["content"] = [{"type": "text", "text": content}]
        elif isinstance(content, list):
            blocks = []
            for part in content:
                if isinstance(part, dict):
                    ptype = part.get("type")
                    if ptype == "text":
                        blocks.append({"type": "text", "text": part.get("text", "")})
                    elif ptype == "image_url":
                        ib = _anthropic_image_block_from_oai_part(part)
                        if ib is not None:
                            blocks.append(ib)
                        else:
                            # drop invalid image part; optional: add a note
                            pass
                    else:
                        # unknown structured part -> stringify to text
                        blocks.append({"type": "text", "text": json.dumps(part, ensure_ascii=False)})
                else:
                    blocks.append({"type": "text", "text": str(part)})
            # if nothing valid landed, at least push empty text
            out_msg["content"] = blocks if blocks else [{"type": "text", "text": ""}]
        else:
            out_msg["content"] = [{"type": "text", "text": str(content)}]

        new_messages.append(out_msg)

    system_blocks: Optional[List[Dict[str, str]]] = None
    if system_texts:
        # Anthropic allows a string OR an array of text blocks;
        # we prefer array of blocks to preserve structure.
        system_blocks = [{"type": "text", "text": s} for s in system_texts if isinstance(s, str)]

    return {"system": system_blocks, "messages": new_messages}

def _map_anthropic_stop_to_openai_finish(stop_reason: Optional[str]) -> Optional[str]:
    if not stop_reason: return None
    if stop_reason in ("end_turn","stop_sequence"): return "stop"
    if stop_reason == "max_tokens": return "length"
    if stop_reason == "tool_use": return "tool_calls"
    return "stop"

def _openai_completion_id() -> str:
    return f"chatcmpl-{uuid.uuid4().hex[:24]}"

# --- OpenAI-compatible Chat Completions -> Anthropic /v1/messages ---
@app.post("/v1/chat/completions")
async def openai_compat_chat_completions(request: Request):
    print(f"[DEBUG] Entering openai_compat_chat_completions function")
    try:
        oai = await request.json()
        print(f"[DEBUG] Parsed JSON request with model: {oai.get('model')}")
    except Exception as e:
        print(f"[DEBUG] Failed to parse JSON: {e}")
        raise HTTPException(status_code=400, detail="invalid json")

    # --- headers for Anthropic
    headers = {"content-type": "application/json", "anthropic-version": request.headers.get("anthropic-version", "2023-06-01")}
    # ask upstream for SSE explicitly
    headers["accept"] = "text/event-stream"

    # auth passthrough / fallback
    if FORWARD_CLIENT_KEY:
        auth = request.headers.get("authorization")
        xkey = request.headers.get("x-api-key")
        if auth: headers["authorization"] = auth
        if xkey: headers["x-api-key"] = xkey
    if "x-api-key" not in headers and SERVER_API_KEY:
        headers["x-api-key"] = SERVER_API_KEY

    # --- map OpenAI -> Anthropic
    stream = bool(oai.get("stream"))
    oai_model = oai.get("model") or AUTOTEXT_MODEL
    model = MODEL_MAP.get(oai_model, oai_model)

    # lift system role to top-level blocks
    system_blocks, anth_messages = [], []
    print(f"[DEBUG] Starting to process {len(oai.get('messages', []))} messages")
    for m in oai.get("messages", []):
        role, content = m.get("role"), m.get("content")
        if role == "system":
            if isinstance(content, str):
                system_blocks.append({"type": "text", "text": content})
            elif isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") in ("text", "input_text"):
                        system_blocks.append({"type": "text", "text": c.get("text", "")})
            continue
        blocks = []
        if isinstance(content, str):
            blocks.append({"type": "text", "text": content})
        elif isinstance(content, list):
            for c in content or []:
                if not isinstance(c, dict): 
                    continue
                t = c.get("type")
                if t in ("text", "input_text"):
                    blocks.append({"type": "text", "text": c.get("text", "")})
                elif t in ("image_url", "image"):
                    print(f"[DEBUG] Processing image content with type: {t}")
                    print(f"[DEBUG] Content dict: {c}")
                    try:
                        # Use the existing helper function for robust image processing
                        ib = _anthropic_image_block_from_oai_part(c)
                        if ib is not None:
                            blocks.append(ib)
                        else:
                            print(f"[DEBUG] Invalid image part, skipping")
                    except Exception as e:
                        print(f"[DEBUG] Error in image processing: {e}")
                        raise HTTPException(status_code=400, detail=f"Invalid image format: {e}")
        elif isinstance(content, dict) and "image_url" in content:
            print(f"[DEBUG] Processing dict content with image_url: {content}")
            try:
                # Convert to the expected format and use the helper function
                image_part = {"type": "image_url", "image_url": content.get("image_url")}
                ib = _anthropic_image_block_from_oai_part(image_part)
                if ib is not None:
                    blocks.append(ib)
                else:
                    print(f"[DEBUG] Invalid image part, skipping")
            except Exception as e:
                print(f"[DEBUG] Error in dict image processing: {e}")
                raise HTTPException(status_code=400, detail=f"Invalid image format: {e}")
        else:
            blocks.append({"type": "text", "text": json.dumps(content, ensure_ascii=False)})
        anth_messages.append({"role": "assistant" if role == "assistant" else "user", "content": blocks})

    print(f"[DEBUG] Finished processing all messages, anth_messages count: {len(anth_messages)}")
    max_tokens = oai.get("max_tokens")
    if not isinstance(max_tokens, int) or max_tokens <= 0:
        max_tokens = 98_304

    anth_payload = {"model": model, "messages": anth_messages, "max_tokens": max_tokens}
    if system_blocks:
        anth_payload["system"] = system_blocks
    if "temperature" in oai and isinstance(oai["temperature"], (int, float)):
        anth_payload["temperature"] = float(oai["temperature"])
    if "stop" in oai:
        anth_payload["stop_sequences"] = [oai["stop"]] if isinstance(oai["stop"], str) else [str(s) for s in oai["stop"]]

    # Check if we should route to OpenAI-compatible endpoint for image models
    has_images = payload_has_image({"messages": oai.get("messages", [])})
    use_openai_endpoint = should_use_openai_endpoint(model, has_images)
    print(f"[DEBUG] Model: {model}, has_images: {has_images}, use_openai_endpoint: {use_openai_endpoint}")
    
    if use_openai_endpoint:
        print(f"[DEBUG] Routing to OpenAI endpoint for model {model} (has_images: {has_images})")
        # For OpenAI-compatible endpoint, convert OpenAI format to simple format
        upstream_payload = convert_openai_to_simple_format(oai)
        # Ensure we use the vision model for image requests
        if has_images and upstream_payload.get("model") != AUTOVISION_MODEL:
            upstream_payload["model"] = AUTOVISION_MODEL
        upstream_url = OPENAI_UPSTREAM_BASE.rstrip("/") + "/chat/completions"
        # Use OpenAI-compatible headers - reset headers for OpenAI endpoint
        headers = {"content-type": "application/json"}
        if FORWARD_CLIENT_KEY:
            auth = request.headers.get("authorization")
            xkey = request.headers.get("x-api-key")
            if auth: headers["authorization"] = auth
            if xkey: headers["x-api-key"] = xkey
        if "authorization" not in headers and "x-api-key" not in headers and SERVER_API_KEY:
            headers["authorization"] = f"Bearer {SERVER_API_KEY}"
    else:
        print(f"[DEBUG] Routing to Anthropic endpoint for model {model}")
        # For Anthropic endpoint, use converted payload
        upstream_payload = anth_payload
        upstream_url = UPSTREAM_BASE.rstrip("/") + "/v1/messages"
        # Keep existing Anthropic headers (already set above)

    # -------------- STREAM path --------------
    if stream:
        # IMPORTANT: enable streaming upstream
        upstream_payload["stream"] = True
        last_seen_usage: Optional[Dict[str, Any]] = None
        last_usage_oai: Optional[Dict[str, Optional[int]]] = None

        async def synthesize_from_json(j: dict):
            # OpenAI-style stream from non-stream Anthropic JSON
            text_out = ""
            for blk in j.get("content", []) or []:
                if isinstance(blk, dict) and blk.get("type") == "text":
                    text_out += blk.get("text", "")
            # role chunk
            yield ('data: ' + json.dumps({
                "id": "chatcmpl_proxy",
                "object": "chat.completion.chunk",
                "model": oai_model,
                "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
            }) + '\n\n').encode('utf-8')
            # content chunks (you can chunk the text if you want finer granularity)
            if text_out:
                yield ('data: ' + json.dumps({
                    "id": "chatcmpl_proxy",
                    "object": "chat.completion.chunk",
                    "model": oai_model,
                    "choices": [{"index": 0, "delta": {"content": text_out}, "finish_reason": None}]
                }) + '\n\n').encode('utf-8')
            # end
            final_chunk = {
                "id": "chatcmpl_proxy",
                "object": "chat.completion.chunk",
                "model": oai_model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
            }
            usage = convert_usage_to_openai(j.get("usage"))
            if any(v is not None for v in usage.values()):
                final_chunk["usage"] = usage
            yield ('data: ' + json.dumps(final_chunk) + '\n\n').encode('utf-8')
            yield b'data: [DONE]\n\n'

        async def gen():
            nonlocal last_seen_usage, last_usage_oai
            async with httpx.AsyncClient(timeout=httpx.Timeout(
                connect=CONNECT_TIMEOUT,
                read=STREAM_TIMEOUT,
                write=REQUEST_TIMEOUT,
                pool=REQUEST_TIMEOUT
            )) as client:
                try:
                    # Correct signature: method first, then URL
                    # Filter out None values from headers to prevent TypeError
                    filtered_headers = {k: v for k, v in headers.items() if v is not None}
                    async with aconnect_sse(client, "POST", upstream_url, headers=filtered_headers, json=upstream_payload) as es:
                        # emit initial role chunk only for Anthropic endpoints
                        if not use_openai_endpoint:
                            yield ('data: ' + json.dumps({
                                "id": "chatcmpl_proxy",
                                "object": "chat.completion.chunk",
                                "model": oai_model,
                                "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
                            }) + '\n\n').encode('utf-8')

                        try:
                            async for ev in es.aiter_sse():
                                if not ev.data:
                                    continue
                                
                                if use_openai_endpoint:
                                    # For OpenAI endpoint, apply token scaling and forward
                                    if ev.data == "[DONE]":
                                        yield b'data: [DONE]\n\n'
                                        return
                                    
                                    # Parse and scale OpenAI streaming response
                                    try:
                                        chunk_data = json.loads(ev.data)
                                        upstream_endpoint = _get_endpoint_type(use_openai_endpoint)
                                        downstream_endpoint = "openai"
                                        scaled_chunk = _scale_openai_streaming_chunk(
                                            chunk_data, upstream_endpoint, downstream_endpoint, model, has_images
                                        )
                                        yield f'data: {json.dumps(scaled_chunk)}\n\n'.encode('utf-8')
                                    except Exception:
                                        # Fallback to original data if parsing fails
                                        yield f'data: {ev.data}\n\n'.encode('utf-8')
                                else:
                                    # For Anthropic endpoint, convert to OpenAI format
                                    msg = None
                                    try:
                                        msg = json.loads(ev.data)
                                    except Exception:
                                        continue
                                    if isinstance(msg, (dict, list)):
                                        found = deep_search_for_usage(msg)
                                        if found and found != last_seen_usage:
                                            last_seen_usage = found
                                            last_usage_oai = convert_usage_to_openai(found)
                                            usage_log = {k: found.get(k) for k in ("input_tokens","output_tokens","cache_creation_input_tokens","cache_read_input_tokens") if k in found}
                                            if DEBUG:
                                                print(f"[DEBUG] streaming usage: {usage_log}")
                                    t = msg.get("type")
                                    if t == "content_block_delta":
                                        d = msg.get("delta") or {}
                                        if d.get("type") == "text_delta":
                                            piece = d.get("text", "")
                                            if piece:
                                                yield ('data: ' + json.dumps({
                                                    "id": "chatcmpl_proxy",
                                                    "object": "chat.completion.chunk",
                                                    "model": oai_model,
                                                    "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}]
                                                }) + '\n\n').encode('utf-8')
                                    elif t == "message_stop":
                                        final_chunk = {
                                            "id": "chatcmpl_proxy",
                                            "object": "chat.completion.chunk",
                                            "model": oai_model,
                                            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                                        }
                                        if isinstance(last_usage_oai, dict) and any(v is not None for v in last_usage_oai.values()):
                                            final_chunk["usage"] = last_usage_oai
                                        
                                        # Apply token scaling for Anthropic -> OpenAI streaming
                                        upstream_endpoint = _get_endpoint_type(use_openai_endpoint)
                                        downstream_endpoint = "openai"
                                        scaled_final_chunk = _scale_openai_streaming_chunk(
                                            final_chunk, upstream_endpoint, downstream_endpoint, model, has_images
                                        )
                                        
                                        yield ('data: ' + json.dumps(scaled_final_chunk) + '\n\n').encode('utf-8')
                                        yield b'data: [DONE]\n\n'
                                        return
                        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as stream_err:
                            # Connection lost during streaming - emit error and close
                            if DEBUG:
                                print(f"[DEBUG] Stream connection lost: {stream_err}")
                            yield ('data: ' + json.dumps({
                                "error": {"message": "Connection to upstream server lost", "type": "connection_error"}, 
                                "id": "chatcmpl_proxy", 
                                "object": "chat.completion.chunk",
                                "model": oai_model
                            }) + '\n\n').encode('utf-8')
                            yield b'data: [DONE]\n\n'
                            return
                        # defensive end
                        yield b'data: [DONE]\n\n'

                except SSEError as e:
                    # Upstream didn’t stream (Content-Type JSON or error). Fallback: get JSON once and synthesize SSE.
                    async with httpx.AsyncClient(timeout=httpx.Timeout(
                        connect=CONNECT_TIMEOUT,
                        read=REQUEST_TIMEOUT,
                        write=REQUEST_TIMEOUT,
                        pool=REQUEST_TIMEOUT
                    )) as client2:
                        # Filter out None values and accept header to prevent TypeError
                        filtered_headers = {k:v for k,v in headers.items() if v is not None and k.lower()!="accept"}
                        r = await client2.post(upstream_url, headers=filtered_headers, json={**upstream_payload, "stream": False})
                        if r.status_code >= 400:
                            # stream an error frame then DONE
                            try:
                                err = r.json()
                            except Exception:
                                err = {"message": r.text}
                            yield ('data: ' + json.dumps({"error": err, "status": r.status_code}) + '\n\n').encode('utf-8')
                            yield b'data: [DONE]\n\n'
                            return
                        try:
                            j = r.json()
                        except Exception:
                            j = {"content": [{"type":"text","text": r.text}]}
                        async for chunk in synthesize_from_json(j):
                            yield chunk
                except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError, ConnectionLostError) as conn_err:
                    # Connection failed - emit error and close
                    if DEBUG:
                        print(f"[DEBUG] Connection failed: {conn_err}")
                    yield ('data: ' + json.dumps({
                        "error": {"message": "Connection to upstream server failed", "type": "connection_error"},
                        "id": "chatcmpl_proxy", 
                        "object": "chat.completion.chunk",
                        "model": oai_model
                    }) + '\n\n').encode('utf-8')
                    yield b'data: [DONE]\n\n'
                    return
                except Exception as e:
                    # final fallback: emit error chunk
                    yield ('data: ' + json.dumps({"error": {"message": repr(e)}}) + '\n\n').encode('utf-8')
                    yield b'data: [DONE]\n\n'

        resp = StreamingResponse(gen(), media_type="text/event-stream")
        resp.headers["X-Proxy-Stream-Fallback"] = "auto"
        return resp

    # -------------- NON-STREAM path --------------
    timeout_config = httpx.Timeout(
        connect=CONNECT_TIMEOUT,
        read=REQUEST_TIMEOUT,
        write=REQUEST_TIMEOUT,
        pool=REQUEST_TIMEOUT
    )
    async with httpx.AsyncClient(timeout=timeout_config) as client:
        try:
            # Filter out None values and accept header to prevent TypeError
            filtered_headers = {k:v for k,v in headers.items() if v is not None and k.lower()!="accept"}
            r = await client.post(upstream_url, headers=filtered_headers, json=upstream_payload)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError, ConnectionLostError) as conn_err:
            if DEBUG:
                print(f"[DEBUG] Non-stream connection failed: {conn_err}")
            detail = {"error": {"message": "Failed to connect to upstream server", "type": "connection_error"}}
            return Response(content=json.dumps(detail), status_code=502, media_type="application/json")
        
        if r.status_code >= 400:
            detail = {"status": r.status_code}
            try:
                detail["upstream"] = r.json()
            except Exception:
                detail["upstream_text"] = r.text
            return Response(content=json.dumps(detail), status_code=500, media_type="application/json")
        j = r.json()

    if use_openai_endpoint:
        # For OpenAI endpoint, return response with scaled tokens
        try:
            response_json = r.json()
            upstream_endpoint = _get_endpoint_type(use_openai_endpoint)
            downstream_endpoint = "openai"  # Always returning OpenAI format
            scaled_response = _scale_openai_response_tokens(
                response_json, upstream_endpoint, downstream_endpoint, model, has_images
            )
            return Response(content=json.dumps(scaled_response), status_code=r.status_code, media_type="application/json")
        except Exception:
            # Fallback to original response if JSON parsing fails
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    else:
        # For Anthropic endpoint, convert response to OpenAI format
        text_out = ""
        for blk in j.get("content", []) or []:
            if isinstance(blk, dict) and blk.get("type") == "text":
                text_out += blk.get("text", "")

        usage = convert_usage_to_openai(j.get("usage"))

        oai_resp = {
            "id": j.get("id", "chatcmpl_proxy"),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": oai_model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": text_out},
                "finish_reason": j.get("stop_reason") or "stop",
            }],
            "usage": usage,
        }
        
        # Apply token scaling for Anthropic -> OpenAI conversion
        upstream_endpoint = _get_endpoint_type(use_openai_endpoint)
        downstream_endpoint = "openai"
        scaled_response = _scale_openai_response_tokens(
            oai_resp, upstream_endpoint, downstream_endpoint, model, has_images
        )
        
        return Response(content=json.dumps(scaled_response), media_type="application/json")

# ---------------------- Anthropic /v1/messages ----------------------
@app.post("/v1/messages")
async def messages_proxy(request: Request):
    req_id = uuid.uuid4().hex[:12]
    try:
        payload = await request.json()
    except Exception as e:
        _write_log("err","messages",req_id,{"where":"parse_json","exc":_exc_info(e)})
        raise HTTPException(status_code=400, detail="invalid json")

    _write_log("req","messages",req_id,{"headers":dict(request.headers),"payload":payload})

    # Auto model switch
    if isinstance(payload, dict):
        incoming_model = payload.get("model")
        img_present = payload_has_image(payload)
        if not incoming_model:
            payload["model"] = AUTOVISION_MODEL if img_present else AUTOTEXT_MODEL
        else:
            if img_present and incoming_model == AUTOTEXT_MODEL: payload["model"] = AUTOVISION_MODEL
            elif (not img_present) and incoming_model == AUTOVISION_MODEL: payload["model"] = AUTOTEXT_MODEL

    if isinstance(payload, dict) and payload.get("model"):
        if payload["model"] in MODEL_MAP: payload["model"] = MODEL_MAP[payload["model"]]
    else:
        if isinstance(payload, dict):
            payload["model"] = AUTOVISION_MODEL if payload_has_image(payload) else AUTOTEXT_MODEL

    headers = {"content-type":"application/json"}
    anthropic_beta = request.headers.get("anthropic-beta")
    anthropic_version = request.headers.get("anthropic-version")
    if anthropic_beta: headers["anthropic-beta"] = anthropic_beta
    if anthropic_version: headers["anthropic-version"] = anthropic_version
    if (not anthropic_beta) and FORCE_ANTHROPIC_BETA and payload_has_cache_control(payload):
        headers["anthropic-beta"] = DEFAULT_ANTHROPIC_BETA

    client_xkey = request.headers.get("x-api-key")
    client_auth = request.headers.get("authorization")
    if FORWARD_CLIENT_KEY and (client_xkey or client_auth):
        if client_xkey: headers["x-api-key"] = client_xkey
        else: headers["authorization"] = client_auth
    else:
        if SERVER_API_KEY: headers["x-api-key"] = SERVER_API_KEY

    try:
        if isinstance(payload, dict) and "messages" in payload:
            local_estimate = count_tokens_from_messages(payload["messages"])
        elif isinstance(payload, dict) and "text" in payload:
            local_estimate = len((ENCODING.encode(payload["text"]) if ENCODING else payload["text"].encode("utf-8"))) // (1 if ENCODING else 4)
        else:
            s = json.dumps(payload); local_estimate = len((ENCODING.encode(s) if ENCODING else s.encode("utf-8"))) // (1 if ENCODING else 4)
    except Exception as e:
        local_estimate = None
        _write_log("err","messages",req_id,{"where":"local_token_estimate","exc":_exc_info(e)})

    size, digest = payload_metadata(payload)
    print(f"[DEBUG] /v1/messages payload_size={size} bytes payload_sha256={digest}")
    print(f"[DEBUG] /v1/messages local_token_estimate: {local_estimate}")

    print(f"[DEBUG] model_autoswitch: image_present={payload_has_image(payload)} -> model={payload.get('model')}")

    upstream_url = UPSTREAM_BASE.rstrip("/") + "/v1/messages"

    # SSE path
    timeout_config = httpx.Timeout(
        connect=CONNECT_TIMEOUT,
        read=STREAM_TIMEOUT,
        write=REQUEST_TIMEOUT,
        pool=REQUEST_TIMEOUT
    )
    async with httpx.AsyncClient(timeout=timeout_config) as client:
        try:
            # Filter out None values from headers to prevent TypeError
            filtered_headers = {k: v for k, v in headers.items() if v is not None}
            async with aconnect_sse(client, "POST", upstream_url, headers=filtered_headers, json=payload) as event_source:
                async def sse_forwarder():
                    last_seen_usage: Optional[Dict[str, Any]] = None
                    _write_log("stream","messages",req_id,{"started":True,"payload_sha256":digest})

                    try:
                        async for event in event_source.aiter_sse():
                            ev_name = getattr(event, "event", None)
                            data_text = getattr(event, "data", None)

                            out_event = ev_name
                            out_data_text = data_text
                            parsed = None
                            try:
                                parsed = json.loads(data_text) if data_text else None
                            except Exception as e:
                                _write_log("err","messages",req_id,{"where":"sse_parse","exc":_exc_info(e)})
                                parsed = None

                            if out_event: yield f"event: {out_event}\n".encode("utf-8")
                            if out_data_text is not None: yield f"data: {out_data_text}\n\n".encode("utf-8")

                            if isinstance(parsed, (dict, list)):
                                found = deep_search_for_usage(parsed)
                                if found and found != last_seen_usage:
                                    last_seen_usage = found
                                    usage_log = {k: found.get(k) for k in ("input_tokens","output_tokens","cache_creation_input_tokens","cache_read_input_tokens") if k in found}
                                    if DEBUG:
                                        print(f"[DEBUG] streaming usage: {usage_log}")
                    except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as stream_err:
                        # Connection lost during streaming - emit error and close stream
                        if DEBUG:
                            print(f"[DEBUG] /v1/messages stream connection lost: {stream_err}")
                        _write_log("err","messages",req_id,{"where":"stream_connection_lost","exc":_exc_info(stream_err)})
                        yield f"event: error\n".encode("utf-8")
                        yield f"data: {json.dumps({'error': {'message': 'Connection to upstream server lost', 'type': 'connection_error'}})}\n\n".encode("utf-8")
                        return
                    except Exception as e:
                        # Other streaming errors
                        if DEBUG:
                            print(f"[DEBUG] /v1/messages stream error: {e}")
                        _write_log("err","messages",req_id,{"where":"stream_error","exc":_exc_info(e)})
                        yield f"event: error\n".encode("utf-8")
                        yield f"data: {json.dumps({'error': {'message': str(e), 'type': 'stream_error'}})}\n\n".encode("utf-8")
                        return

                resp = StreamingResponse(sse_forwarder(), media_type="text/event-stream")
                _write_log("resp","messages",req_id,{"streaming":True})
                return resp
        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError, ConnectionLostError) as conn_err:
            if DEBUG:
                print(f"[DEBUG] /v1/messages initial connection failed: {conn_err}")
            _write_log("err","messages",req_id,{"where":"sse_connect_failed","exc":_exc_info(conn_err)})
            # fall through to non-stream
        except Exception as e:
            _write_log("err","messages",req_id,{"where":"sse_connect","exc":_exc_info(e)})
            # fall through to non-stream

        # Fallback non-stream
        try:
            # DEBUG: Log headers before request to identify None values
            if DEBUG:
                print(f"[DEBUG] Messages endpoint headers before upstream request: {headers}")
                none_headers = {k: v for k, v in headers.items() if v is None}
                if none_headers:
                    print(f"[DEBUG] Messages endpoint found None headers: {none_headers}")
            # Filter out None values from headers to prevent TypeError
            filtered_headers = {k: v for k, v in headers.items() if v is not None}
            r = await _post_with_retries(client, upstream_url, json=payload, headers=filtered_headers)
        except ConnectionLostError as conn_err:
            _write_log("err","messages",req_id,{"where":"connection_lost","exc":_exc_info(conn_err)})
            raise HTTPException(status_code=502, detail="Connection to upstream server lost")
        except httpx.HTTPError as e:
            _write_log("err","messages",req_id,{"where":"fallback_post","exc":_exc_info(e)})
            raise HTTPException(status_code=502, detail=f"upstream error: {e}")

        response_headers = dict(r.headers)
        content_bytes = r.content
        status = r.status_code

        parsed = None
        try:
            parsed = r.json()
        except Exception as e:
            _write_log("err","messages",req_id,{"where":"fallback_parse_json","exc":_exc_info(e)})
            parsed = None

        if isinstance(parsed, dict):
            usage = parsed.get("usage") if isinstance(parsed, dict) else None
            if isinstance(usage, dict):
                usage_log = {k: usage.get(k) for k in ("input_tokens","output_tokens","cache_creation_input_tokens","cache_read_input_tokens") if k in usage}
                print(f"[DEBUG] upstream /v1/messages status={status}, usage={usage_log}")
        elif parsed is None and content_bytes and b"event:" in content_bytes and b"data:" in content_bytes:
            found_usage = parse_sse_bytes_for_usage(content_bytes)
            if found_usage:
                usage_log = {k: found_usage.get(k) for k in ("input_tokens","output_tokens","cache_creation_input_tokens","cache_read_input_tokens") if k in found_usage}
                print(f"[DEBUG] fallback buffered SSE: extracted usage: {usage_log}")

        _write_log("resp","messages",req_id,{"status":status,"json":parsed})
        return Response(content=content_bytes, status_code=status, headers=response_headers)

# ---------------------- Health ----------------------
@app.get("/health")
def health():
    return {"ok": True}
