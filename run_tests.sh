#!/bin/bash
# Quick test runner for RDF Converter
# This script starts Docker services and runs the test suite

set -e

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=================================="
echo "RDF Converter Test Runner"
echo "=================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    echo "Please start Docker and try again"
    exit 1
fi

# Check for docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose not found${NC}"
    echo "Please install docker-compose"
    exit 1
fi

# Parse command line arguments
RUN_MODE="${1:-integration}"
VERBOSE="${2:-}"

echo -e "${YELLOW}Starting Docker services...${NC}"

# Start required services
docker-compose up -d yarrrml-parser rmlmapper

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 5

# Check YARRRML Parser health
echo -n "Checking YARRRML Parser... "
if curl -s -f http://localhost:3001/ > /dev/null 2>&1 || curl -s http://localhost:3001/ 2>&1 | grep -q "404\|Cannot GET"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "YARRRML Parser not responding. Check logs:"
    echo "  docker-compose logs yarrrml-parser"
    exit 1
fi

# Check RML Mapper health
echo -n "Checking RML Mapper... "
if curl -s -f http://localhost:4000/ > /dev/null 2>&1 || curl -s http://localhost:4000/ 2>&1 | grep -q "404\|Cannot GET"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "RML Mapper not responding. Check logs:"
    echo "  docker-compose logs rmlmapper"
    exit 1
fi

echo -e "${GREEN}All services are ready!${NC}"
echo ""

# Set environment variables
export YARRRML_URL="http://localhost:3001"
export MAPPER_URL="http://localhost:4000"

# Run tests based on mode
echo "=================================="
echo "Running Tests"
echo "=================================="
echo ""

case "$RUN_MODE" in
    "integration"|"all")
        echo "Running integration tests..."
        if [ "$VERBOSE" == "-v" ] || [ "$VERBOSE" == "--verbose" ]; then
            pytest tests/test_integration_mappings.py -v -s --log-cli-level=INFO
        else
            pytest tests/test_integration_mappings.py -v
        fi
        ;;
    "quick")
        echo "Running quick tests (template and rule verification)..."
        pytest tests/test_integration_mappings.py::test_template_copy_verification \
               tests/test_integration_mappings.py::test_mapping_rules_generate_triples \
               -v
        ;;
    "default")
        echo "Running default mapping test only..."
        pytest tests/test_integration_mappings.py::test_default_mapping_from_ui -v -s --log-cli-level=INFO
        ;;
    "batch")
        echo "Running batch mapping tests only..."
        pytest tests/test_integration_mappings.py::test_batch_mapping_with_json -v -s --log-cli-level=INFO
        ;;
    "coverage")
        echo "Running coverage analysis..."
        pytest tests/test_integration_mappings.py::test_mapping_coverage_analysis -v -s --log-cli-level=INFO
        ;;
    "debug")
        echo "Running with maximum verbosity..."
        pytest tests/test_integration_mappings.py -v -s --log-cli-level=DEBUG
        ;;
    *)
        echo -e "${RED}Unknown mode: $RUN_MODE${NC}"
        echo ""
        echo "Usage: ./run_tests.sh [mode] [verbose]"
        echo ""
        echo "Modes:"
        echo "  integration - Run all integration tests (default)"
        echo "  quick       - Run quick verification tests only"
        echo "  default     - Run default mapping test"
        echo "  batch       - Run batch/JSON mapping test"
        echo "  coverage    - Run coverage analysis"
        echo "  debug       - Run with maximum verbosity"
        echo ""
        echo "Verbose flag: -v or --verbose"
        exit 1
        ;;
esac

TEST_RESULT=$?

echo ""
echo "=================================="

if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ Tests passed!${NC}"
else
    echo -e "${RED}✗ Tests failed${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check service logs: docker-compose logs yarrrml-parser rmlmapper"
    echo "  2. View test output: cat tests/data/batch_test/test_output.ttl"
    echo "  3. Run with debug: ./run_tests.sh debug"
fi

echo "=================================="
echo ""
echo "To stop services: docker-compose down"
echo "To view logs: docker-compose logs -f"
echo ""

exit $TEST_RESULT
