# Testing Guide for RDF Converter

This document provides a quick overview of the testing infrastructure for the RDF Converter application.

## Test API Endpoint

The simplest way to run tests is via the API endpoint:

```bash
# Run tests via API (works in any environment)
curl http://localhost:6003/api/test

# Or access via browser/Swagger UI
http://localhost:6003/api/docs#/transform/run_tests_api_test_get
```

This endpoint:
- ✅ Runs all integration tests
- ✅ Works in deployed environments
- ✅ Returns test results as JSON
- ✅ No local setup required

---

## Quick Start (Local Testing)

```bash
# Make the test runner executable (if not already)
chmod +x run_tests.sh

# Run all integration tests
./run_tests.sh

# Or run specific test modes
./run_tests.sh quick      # Fast verification tests
./run_tests.sh default    # Test default UI mapping
./run_tests.sh batch      # Test JSON/batch mappings
./run_tests.sh coverage   # Get detailed coverage analysis
./run_tests.sh debug      # Maximum verbosity for debugging
```

## What Gets Tested

The test suite verifies the core algorithm of the RDF Converter:

1. **Template Graph Copying** ✓
   - Semantic data template graphs are successfully copied to output
   - This is the trivial but essential first step
   - Generic verification - works with any URL/namespace structure

2. **Mapping Rule Application** ✓
   - Each YARRRML mapping rule generates RDF triples
   - Rules are applied correctly per data structure
   - Both successful and skipped rules are tracked

3. **Data Format Support** ✓
   - CSVW/RDF data sources (the original use case)
   - Plain JSON data sources with JSONPath (newer requirement)

4. **Reference Mapping** ✓
   - Uses: https://raw.githubusercontent.com/Mat-O-Lab/MapToMethod/refs/heads/main/examples/example-map.yaml
   - The official reference mapping that should always work
   - Can optionally use local copy for offline testing

## Test Architecture

```
RDFConverter Application
    ↓
┌─────────────────────────────────────────┐
│  apply_mapping()                        │
│  1. Fetch YARRRML mapping               │
│  2. Convert to RML rules (via Docker)   │
│  3. Fetch template graph                │
│  4. Fetch data file                     │
│  5. Execute RML mapping (via Docker)    │
│  6. Combine template + mapping results  │
│  7. Return: triples, rules applied/skip │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Test Utilities (test_utils.py)        │
│  - Parse RDF output                     │
│  - Verify template triples present      │
│  - Verify mapping triples generated     │
│  - Analyze coverage metrics             │
│  - Assert success criteria              │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Integration Tests                      │
│  - Default mapping (UI example)         │
│  - Batch/JSON mapping                   │
│  - Template verification                │
│  - Rule generation verification         │
│  - Coverage analysis                    │
└─────────────────────────────────────────┘
```

## Key Features

### ✅ Automatic Service Management
Tests automatically start required Docker services (YARRRML Parser, RML Mapper) if not running.

### ✅ Detailed Diagnostics
Each test provides comprehensive output:
- Number of rules defined vs applied
- Total triples generated
- Template vs mapping triples
- Coverage percentage
- Suggestions for failures

### ✅ Multiple Test Modes
- **Integration tests** - Full end-to-end testing
- **Quick tests** - Fast verification (template + rules)
- **Coverage analysis** - Detailed metrics
- **Debug mode** - Maximum logging for troubleshooting

### ✅ Output Inspection
Generated RDF files are saved for manual inspection at:
`tests/data/batch_test/test_output.ttl`

## Prerequisites

### Required Docker Services

The app depends on two microservices:

```yaml
# docker-compose.yml
services:
  yarrrml-parser:  # Port 3001 - Converts YARRRML to RML
  rmlmapper:       # Port 4000 - Executes RML rules
```

### Python Dependencies

```bash
pip install -r tests/requirements.txt
```

## Usage Examples

### Running Tests Manually

```bash
# Start services
docker-compose up -d yarrrml-parser rmlmapper

# Set environment variables
export YARRRML_URL="http://localhost:3001"
export MAPPER_URL="http://localhost:4000"

# Run tests with pytest
pytest tests/test_integration_mappings.py -v

# Run with detailed logging
pytest tests/test_integration_mappings.py -v -s --log-cli-level=INFO
```

### Using the Test Runner Script

```bash
# Run all tests (automatically starts services)
./run_tests.sh

# Run specific test suite
./run_tests.sh batch -v

# Debug a failing test
./run_tests.sh debug
```

### Running Individual Tests

```bash
# Test default mapping
pytest tests/test_integration_mappings.py::test_default_mapping_from_ui -v -s

# Test JSON/batch mapping
pytest tests/test_integration_mappings.py::test_batch_mapping_with_json -v -s

# Test template copying
pytest tests/test_integration_mappings.py::test_template_copy_verification -v
```

## Understanding Test Output

### Success Example
```
==================== MAPPING TEST SUMMARY ====================
Success: ✓
Total Rules: 11
Rules Applied: 9
Rules Skipped: 2
Total Triples Generated: 156
Rule Coverage: 81.8%
Template Triples Found: ✓
Mapping Triples Found: ✓
==============================================================
PASSED ✓
```

### Failure Example
```
==================== MAPPING TEST SUMMARY ====================
Success: ✗
Total Rules: 11
Rules Applied: 0
Rules Skipped: 11
Total Triples Generated: 45 (template only)
Rule Coverage: 0.0%
Template Triples Found: ✓
Mapping Triples Found: ✗
==============================================================
FAILED - No mapping triples generated
```

## Troubleshooting

### Services Not Starting
```bash
# Check Docker is running
docker ps

# Check service logs
docker-compose logs yarrrml-parser
docker-compose logs rmlmapper

# Restart services
docker-compose restart yarrrml-parser rmlmapper
```

### No Triples Generated
```bash
# Run with debug logging
./run_tests.sh debug

# Check RML mapper logs
docker-compose logs rmlmapper

# Verify mapping file structure
cat tests/data/batch_test/batch_mapping.yaml
```

### Tests Hanging
```bash
# Check service health
curl http://localhost:3001/
curl http://localhost:4000/

# Check for port conflicts
netstat -an | grep 3001
netstat -an | grep 4000
```

## Test Files

| File | Purpose |
|------|---------|
| `tests/conftest.py` | Pytest configuration, fixtures, service management |
| `tests/test_utils.py` | Utilities for parsing, verification, diagnostics |
| `tests/test_integration_mappings.py` | Main integration test suite |
| `tests/requirements.txt` | Test dependencies |
| `tests/README.md` | Detailed testing documentation |
| `pytest.ini` | Pytest configuration |
| `run_tests.sh` | Convenient test runner script |

## Test Data

Sample mappings and data for testing:

| Directory | Contents |
|-----------|----------|
| `tests/data/batch_test/` | JSON batch mapping test files |
| `tests/data/yarrrmltorml/` | YARRRML to RML conversion tests |

## Success Criteria

A mapping test passes when:

1. ✓ At least one mapping rule generates triples
2. ✓ Template graph is copied to output
3. ✓ New triples are generated beyond template
4. ✓ Minimum coverage percentage is met (varies by test)

## Integration with CI/CD

The tests can be easily integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Start services
  run: docker-compose up -d yarrrml-parser rmlmapper

- name: Run tests
  run: |
    export YARRRML_URL="http://localhost:3001"
    export MAPPER_URL="http://localhost:4000"
    pytest tests/test_integration_mappings.py -v
```

## Further Documentation

For detailed information, see:
- **[tests/README.md](tests/README.md)** - Comprehensive testing guide
- **[tests/README_BATCH_TEST.md](tests/README_BATCH_TEST.md)** - Batch mapping debugging notes

## Support

If tests fail:
1. Check service logs: `docker-compose logs`
2. View test output: `cat tests/data/batch_test/test_output.ttl`
3. Run with debug: `./run_tests.sh debug`
4. Review detailed documentation in `tests/README.md`

---

**Key Insight:** The hard part isn't copying the template graph (that works and is trivial), but verifying that each mapping rule generates the expected triples. These tests focus on that critical aspect.
