#!/usr/bin/env python3
"""
Fix for Concurrent Cache Access Issues

This script provides the necessary modifications to fix the global shared state
issue in the image description cache system that could cause requests to get stuck.

Apply these changes to src/main.py to resolve race conditions in cache access.
"""

import asyncio

# Add these imports and global variables to src/main.py

# ============================================================================
# ADDITIONS TO src/main.py
# ============================================================================

# Add this import near the top of the file with other imports
import threading

# Add these global variables after the existing cache metadata declaration
# (around line 220, after: image_description_cache_metadata = {})

# Lock for thread-safe cache access
cache_lock = asyncio.Lock()
cache_access_stats = {
    "hits": 0,
    "misses": 0,
    "errors": 0,
    "concurrent_access": 0
}

# ============================================================================
# MODIFIED FUNCTIONS
# ============================================================================

# Replace the existing load_cache_from_file function with this version:
async def load_cache_from_file_fixed(cache_key: str) -> Optional[str]:
    """Load cached description from file asynchronously with thread-safe access."""
    async with cache_lock:
        try:
            # Track concurrent access
            cache_access_stats["concurrent_access"] += 1
            
            if cache_key in image_description_cache_metadata:
                file_path = image_description_cache_metadata[cache_key]["file_path"]
                if Path(file_path).exists():
                    async with aiofiles.open(file_path, 'rb') as f:
                        content = await f.read()
                        description = pickle.loads(content)
                        cache_access_stats["hits"] += 1
                        if CACHE_ENABLE_LOGGING:
                            print(f"[CACHE HIT] Loaded from file: {cache_key[:16]}..., size: {len(content)} bytes")
                        return description
                else:
                    # File doesn't exist, remove from metadata
                    del image_description_cache_metadata[cache_key]
                    if CACHE_ENABLE_LOGGING:
                        print(f"[CACHE CLEANUP] Removed missing file reference: {cache_key[:16]}...")
            cache_access_stats["misses"] += 1
            return None
        except Exception as e:
            cache_access_stats["errors"] += 1
            if CACHE_ENABLE_LOGGING:
                print(f"[CACHE ERROR] Failed to load cache {cache_key[:16]}...: {e}")
            return None

# Replace the existing save_cache_to_file function with this version:
async def save_cache_to_file_fixed(cache_key: str, description: str) -> None:
    """Save description to cache file asynchronously with thread-safe access (fire and forget)."""
    async with cache_lock:
        try:
            # Track concurrent access
            cache_access_stats["concurrent_access"] += 1
            
            # Generate file name based on cache key hash
            file_hash = hashlib.sha256(cache_key.encode()).hexdigest()[:16]
            file_name = f"{CACHE_FILE_PREFIX}{file_hash}{CACHE_FILE_EXTENSION}"
            file_path = CACHE_DIR / file_name
            
            # Serialize description
            data = pickle.dumps(description)
            
            # Save to file
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(data)
            
            # Update metadata
            image_description_cache_metadata[cache_key] = {
                "file_path": str(file_path),
                "timestamp": time.time(),
                "size": len(data)
            }
            
            if CACHE_ENABLE_LOGGING:
                print(f"[CACHE STORE] Saved to file: {cache_key[:16]}..., size: {len(data)} bytes, total entries: {len(image_description_cache_metadata)}")
                
        except Exception as e:
            cache_access_stats["errors"] += 1
            if CACHE_ENABLE_LOGGING:
                print(f"[CACHE ERROR] Failed to save cache {cache_key[:16]}...: {e}")

# Replace the existing cleanup_cache_if_needed function with this version:
async def cleanup_cache_if_needed_fixed() -> None:
    """Clean up old cache files when limit is exceeded (thread-safe)."""
    async with cache_lock:
        try:
            if len(image_description_cache_metadata) > IMAGE_DESCRIPTION_CACHE_SIZE:
                # Sort by timestamp (oldest first)
                sorted_entries = sorted(
                    image_description_cache_metadata.items(),
                    key=lambda x: x[1]["timestamp"]
                )
                
                # Remove oldest entries
                items_to_remove = len(image_description_cache_metadata) - IMAGE_DESCRIPTION_CACHE_SIZE + 100
                removed_count = 0
                total_size_removed = 0
                
                for cache_key, metadata in sorted_entries[:items_to_remove]:
                    try:
                        file_path = Path(metadata["file_path"])
                        if file_path.exists():
                            file_path.unlink()
                            total_size_removed += metadata.get("size", 0)
                        del image_description_cache_metadata[cache_key]
                        removed_count += 1
                    except Exception as cleanup_error:
                        if CACHE_ENABLE_LOGGING:
                            print(f"[CACHE CLEANUP ERROR] Failed to remove {cache_key[:16]}...: {cleanup_error}")
                
                if CACHE_ENABLE_LOGGING:
                    print(f"[CACHE CLEANUP] Removed {removed_count} files ({total_size_removed} bytes), cache entries: {len(image_description_cache_metadata)}")
                    
        except Exception as e:
            cache_access_stats["errors"] += 1
            if CACHE_ENABLE_LOGGING:
                print(f"[CACHE CLEANUP ERROR] Cleanup failed: {e}")

# ============================================================================
# ADDITIONAL MONITORING FUNCTIONS
# ============================================================================

def get_cache_stats() -> Dict[str, Any]:
    """Get cache performance statistics for monitoring."""
    return {
        "metadata_entries": len(image_description_cache_metadata),
        "cache_hits": cache_access_stats["hits"],
        "cache_misses": cache_access_stats["misses"],
        "cache_errors": cache_access_stats["errors"],
        "concurrent_access_count": cache_access_stats["concurrent_access"],
        "hit_rate": cache_access_stats["hits"] / max(1, cache_access_stats["hits"] + cache_access_stats["misses"]) * 100
    }

def reset_cache_stats() -> None:
    """Reset cache statistics for monitoring."""
    global cache_access_stats
    cache_access_stats = {
        "hits": 0,
        "misses": 0,
        "errors": 0,
        "concurrent_access": 0
    }

# ============================================================================
# USAGE INSTRUCTIONS
# ============================================================================

"""
HOW TO APPLY THIS FIX:

1. Add the import and global variables to src/main.py:
   import threading
   
   cache_lock = asyncio.Lock()
   cache_access_stats = {
       "hits": 0,
       "misses": 0,
       "errors": 0,
       "concurrent_access": 0
   }

2. Replace the existing functions:
   - load_cache_from_file -> load_cache_from_file_fixed
   - save_cache_to_file -> save_cache_to_file_fixed
   - cleanup_cache_if_needed -> cleanup_cache_if_needed_fixed

3. Update all function calls to use the new function names:
   - In generate_image_descriptions: await load_cache_from_file_fixed(cache_key)
   - In generate_image_descriptions: await save_cache_to_file_fixed(cache_key, description)
   - In startup_event: await cleanup_cache_if_needed_fixed()

4. Add monitoring endpoint (optional):
@app.get("/debug/cache-stats")
async def get_cache_statistics():
    return get_cache_stats()

@app.post("/debug/cache-stats/reset")
async def reset_cache_statistics():
    reset_cache_stats()
    return {"status": "reset"}

5. Test the fix:
   - Restart the service: docker compose down && docker compose up -d
   - Run the diagnostic script: python debug_concurrent_requests.py
   - Monitor cache stats: curl http://localhost:8000/debug/cache-stats

EXPECTED IMPROVEMENTS:
- Elimination of race conditions in cache access
- Better handling of concurrent requests
- Reduced likelihood of requests getting stuck
- Improved cache performance monitoring
- Thread-safe operations under high load
"""

if __name__ == "__main__":
    print("This is a fix script, not meant to be executed directly.")
    print("Please follow the usage instructions in the comments above.")