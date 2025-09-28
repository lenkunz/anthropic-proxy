# Testing and Development Organization

This document describes the new organized structure for tests, benchmarks, and examples.

## 📁 New Directory Structure

```
anthropic-proxy/
├── main.py                     # Core proxy application
├── .env                        # Environment configuration (project root)
├── docker-compose.yml          # Docker deployment
├── README.md                   # Main project documentation
├── API_DOCUMENTATION.md        # API reference
├── DEVELOPMENT.md              # Development setup
├── PERFORMANCE_ANALYSIS.md     # Performance documentation  
├── OPTIMIZATION_SUMMARY.md     # Optimization results
├── examples/                   # Usage examples
│   ├── README.md              # Examples documentation
│   ├── example_usage.py       # Basic API usage
│   ├── example_model_variants.py # Model routing examples
│   └── example_messages_streaming.py # Streaming examples
└── tests/                     # All testing code
    ├── README.md              # Comprehensive testing guide
    ├── conftest.py            # Shared test utilities
    ├── run_organized_tests.py # Main test runner
    ├── simple_test.py         # Legacy simple test
    ├── run_all_tests.py       # Legacy test runner
    ├── unit/                  # Fast, isolated tests
    │   ├── test_model_variants.py
    │   ├── test_image_detection.py
    │   ├── test_conversion.py
    │   └── test_detection_detailed.py
    ├── integration/           # End-to-end API tests
    │   ├── test_messages_endpoint.py
    │   ├── test_api.py
    │   ├── test_image_processing.py
    │   ├── test_streaming*.py
    │   ├── test_error*.py
    │   ├── test_connection*.py
    │   └── test_*.py
    └── benchmarks/            # Performance testing
        ├── quick_benchmark.py
        ├── comprehensive_benchmark.py
        ├── detailed_profiler.py
        └── benchmark_proxy_overhead.py
```

## 🔧 Key Improvements

### 1. Centralized Environment Loading
All test, benchmark, and example scripts now properly load the `.env` file from the project root:

```python
# Standard pattern used in all files
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent  # Adjust based on depth
load_dotenv(project_root / ".env")
```

### 2. Shared Test Utilities (`tests/conftest.py`)
- Common test functions and helpers
- Environment validation
- Standardized headers and payloads
- Health check functions
- Performance timing utilities

### 3. Categorized Tests
- **Unit Tests**: Fast, isolated functionality testing
- **Integration Tests**: End-to-end API testing requiring running proxy
- **Benchmarks**: Performance analysis and optimization validation

### 4. Comprehensive Documentation
- `tests/README.md`: Complete testing guide
- `examples/README.md`: Example usage guide  
- Category-specific documentation

## 🚀 Quick Usage

### Run All Tests
```bash
python tests/run_organized_tests.py
```

### Run Specific Categories
```bash
# Unit tests (fast)
python tests/unit/test_model_variants.py

# Integration tests (requires proxy running)
python tests/integration/test_messages_endpoint.py

# Performance benchmarks
python tests/benchmarks/quick_benchmark.py
```

### Run Examples
```bash
python examples/example_usage.py
python examples/example_model_variants.py
```

## 🎯 Benefits

### For Development
- **Organized Structure**: Easy to find relevant tests
- **Proper Environment Handling**: No more hardcoded paths or missing .env
- **Shared Utilities**: Common code reused across tests
- **Clear Categories**: Unit vs integration vs performance testing

### For CI/CD
- **Selective Testing**: Run only relevant test categories
- **Clear Dependencies**: Unit tests don't need proxy, integration tests do
- **Performance Monitoring**: Benchmark scripts ready for automated testing

### For Users
- **Clear Examples**: Well-documented usage patterns
- **Easy Testing**: Simple commands to validate setup
- **Performance Validation**: Built-in benchmarking tools

## 📊 Environment Configuration

All scripts read from the project root `.env` file:

```bash
# Required for all tests and examples
SERVER_API_KEY=your_api_key_here

# API endpoints (optional)
UPSTREAM_BASE=https://api.z.ai/api/anthropic
OPENAI_UPSTREAM_BASE=https://api.z.ai/api/coding/paas/v4

# Performance tuning (optional)
HTTP_POOL_CONNECTIONS=20
HTTP_KEEPALIVE_CONNECTIONS=15
CONNECT_TIMEOUT=10.0
REQUEST_TIMEOUT=120.0
STREAM_TIMEOUT=300.0

# Debug mode (optional)
DEBUG=false
```

## 🔄 Migration Notes

### From Old Structure
- All `test_*.py` files moved to appropriate subdirectories
- All `example_*.py` files moved to `examples/`
- All `benchmark_*.py` and `*profiler*.py` files moved to `tests/benchmarks/`
- Environment loading updated in all files to use project root

### Backward Compatibility
- Old test runner scripts still exist: `run_all_tests.py`, `simple_test.py`
- New organized runner: `tests/run_organized_tests.py`
- All functionality preserved, just better organized

## ✅ Validation

The new structure has been tested and validated:
- ✅ Environment loading works from all subdirectories
- ✅ Benchmarks show expected performance results
- ✅ Unit tests execute successfully
- ✅ Integration tests connect to proxy properly
- ✅ Examples demonstrate API usage correctly

---

**Result**: A clean, organized, and maintainable testing structure that properly handles environment configuration and provides clear categories for different types of testing and development activities.