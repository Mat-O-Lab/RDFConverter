"""
Pytest configuration and fixtures for RDF Converter tests
"""
import pytest
import requests
import time
import logging
import os
import subprocess
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Test configuration
# Default to Docker network service names (for running inside container)
# Can be overridden with environment variables for local testing
YARRRML_URL = os.getenv("YARRRML_URL", "http://yarrrml-parser:3001")
MAPPER_URL = os.getenv("MAPPER_URL", "http://rmlmapper:4000")
APP_URL = os.getenv("APP_URL", "http://localhost:5000")

# Service health check configuration
MAX_RETRIES = 30
RETRY_DELAY = 2  # seconds


def check_service_health(url: str, service_name: str, max_retries: int = MAX_RETRIES) -> bool:
    """
    Check if a service is healthy and responding
    
    Args:
        url: Base URL of the service
        service_name: Name of the service for logging
        max_retries: Maximum number of retry attempts
        
    Returns:
        True if service is healthy, False otherwise
    """
    logger.info(f"Checking health of {service_name} at {url}")
    
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{url}/", timeout=5)
            if response.status_code in [200, 404]:  # 404 is OK, means service is running
                logger.info(f"✓ {service_name} is ready")
                return True
        except requests.exceptions.RequestException as e:
            logger.debug(f"Attempt {attempt + 1}/{max_retries}: {service_name} not ready yet ({e})")
            time.sleep(RETRY_DELAY)
    
    logger.error(f"✗ {service_name} failed to become ready after {max_retries} attempts")
    return False


@pytest.fixture(scope="session")
def docker_services():
    """
    Ensure Docker services are running for tests
    This fixture starts docker-compose if services aren't available
    """
    logger.info("=" * 80)
    logger.info("Checking Docker services...")
    logger.info("=" * 80)
    
    # Check if services are already running
    yarrrml_ready = check_service_health(YARRRML_URL, "YARRRML Parser", max_retries=2)
    mapper_ready = check_service_health(MAPPER_URL, "RML Mapper", max_retries=2)
    
    if yarrrml_ready and mapper_ready:
        logger.info("All services are already running")
        yield {
            "yarrrml_url": YARRRML_URL,
            "mapper_url": MAPPER_URL,
            "app_url": APP_URL
        }
        return
    
    # Services not running, try to start them
    logger.warning("Services not running, attempting to start via docker-compose...")
    
    try:
        # Start services using docker-compose
        subprocess.run(
            ["docker-compose", "up", "-d", "yarrrml-parser", "rmlmapper"],
            check=True,
            cwd="/home/hanke/RDFConverter"
        )
        
        # Wait for services to be ready
        yarrrml_ready = check_service_health(YARRRML_URL, "YARRRML Parser")
        mapper_ready = check_service_health(MAPPER_URL, "RML Mapper")
        
        if not (yarrrml_ready and mapper_ready):
            pytest.skip("Docker services could not be started. Please run: docker-compose up -d")
        
        yield {
            "yarrrml_url": YARRRML_URL,
            "mapper_url": MAPPER_URL,
            "app_url": APP_URL
        }
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start docker services: {e}")
        pytest.skip("Could not start Docker services. Please ensure Docker is running.")
    except FileNotFoundError:
        logger.error("docker-compose command not found")
        pytest.skip("docker-compose not found. Please install Docker Compose.")


@pytest.fixture(scope="session")
def app_context(docker_services):
    """
    Set up application context with service URLs
    """
    os.environ["YARRRML_URL"] = docker_services["yarrrml_url"]
    os.environ["MAPPER_URL"] = docker_services["mapper_url"]
    
    return docker_services


@pytest.fixture
def test_data_dir():
    """Return path to test data directory"""
    return os.path.join(os.path.dirname(__file__), "data")


@pytest.fixture
def batch_test_data(test_data_dir):
    """Provide batch test data files"""
    return {
        "mapping_url": f"file://{test_data_dir}/batch_test/batch_mapping.yaml",
        "data_url": f"file://{test_data_dir}/batch_test/batch_data.json"
    }


@pytest.fixture
def default_mapping_urls(test_data_dir):
    """
    Provide the default mapping URLs used in the UI
    This is the reference example that should always work
    
    Can use either remote URL or local file if available
    """
    # The official reference mapping URL
    remote_mapping_url = "https://raw.githubusercontent.com/Mat-O-Lab/MapToMethod/refs/heads/main/examples/example-map.yaml"
    
    # Check if there's a local copy for testing without network
    local_mapping_file = os.path.join(test_data_dir, "default_mapping", "example-map.yaml")
    
    if os.path.exists(local_mapping_file):
        logger.info(f"Using local default mapping: {local_mapping_file}")
        mapping_url = f"file://{local_mapping_file}"
    else:
        logger.info(f"Using remote default mapping: {remote_mapping_url}")
        mapping_url = remote_mapping_url
    
    return {
        "mapping_url": mapping_url,
        "data_url": None,  # Uses data URL from mapping file
        "remote_url": remote_mapping_url  # Keep reference to remote URL
    }


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring Docker services"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_network: mark test as requiring network access"
    )
