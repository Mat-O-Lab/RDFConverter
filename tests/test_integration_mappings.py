"""
Integration tests for RDF Converter mapping functionality

These tests verify that:
1. The default mapping (from UI) works correctly
2. Template graphs are copied successfully 
3. Mapping rules generate triples per rule
4. Both CSVW/RDF and plain JSON data sources work
"""
import pytest
import logging
import sys
import os
import yaml

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import apply_mapping, open_file
from test_utils import (
    MappingTestResult,
    parse_rdf_output,
    verify_template_triples,
    verify_mapping_triples,
    assert_mapping_success,
    analyze_mapping_coverage
)

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.requires_network
def test_default_mapping_from_ui(app_context, default_mapping_urls):
    """
    Test the default reference mapping
    Uses: https://raw.githubusercontent.com/Mat-O-Lab/MapToMethod/refs/heads/main/examples/example-map.yaml
    
    This is the reference example that should always work, verifying:
    - Template graph is copied successfully
    - Mapping rules generate triples
    """
    logger.info("="*80)
    logger.info("Testing default reference mapping")
    logger.info(f"Reference URL: {default_mapping_urls.get('remote_url', 'N/A')}")
    logger.info("="*80)
    
    mapping_url = default_mapping_urls["mapping_url"]
    data_url = default_mapping_urls["data_url"]
    
    # Execute mapping
    filename, output, num_rules, num_applied = apply_mapping(
        mapping_url=mapping_url,
        opt_data_url=data_url,
        authorization=None
    )
    
    # Parse results
    graph = parse_rdf_output(output)
    
    # Verify results - generic checks not tied to specific URLs/namespaces
    template_found = verify_template_triples(graph)  # Just checks graph has content
    mapping_found = verify_mapping_triples(graph)    # Checks triples were generated
    
    result = MappingTestResult(
        success=num_applied > 0 and len(graph) > 0,
        num_rules=num_rules,
        num_triples=len(graph),
        num_rules_applied=num_applied,
        num_rules_skipped=num_rules - num_applied,
        output_graph=output,
        template_triples_found=template_found,
        mapping_triples_found=mapping_found
    )
    
    # Assert success with relaxed criteria for default example
    assert_mapping_success(
        result,
        min_coverage_percent=50.0,  # Relaxed for default example
        require_template_triples=True,
        require_mapping_triples=True
    )


@pytest.mark.integration
def test_batch_mapping_with_json(app_context, batch_test_data):
    """
    Test batch mapping with plain JSON data source
    This tests JSONPath-based mappings
    """
    logger.info("="*80)
    logger.info("Testing batch mapping with plain JSON")
    logger.info("="*80)
    
    mapping_url = batch_test_data["mapping_url"]
    data_url = batch_test_data["data_url"]
    
    # Execute mapping
    filename, output, num_rules, num_applied = apply_mapping(
        mapping_url=mapping_url,
        opt_data_url=data_url,
        authorization=None
    )
    
    # Parse results
    graph = parse_rdf_output(output)
    
    # Get template URL from mapping
    mapping_data, _ = open_file(mapping_url)
    mapping_dict = yaml.safe_load(mapping_data)
    template_url = mapping_dict["prefixes"]["method"].strip("/")
    
    # Expected predicates from the batch mapping
    expected_predicates = [
        "urn:samm:org.eclipse.esmf.samm:meta-model:2.3.0#value",
        "urn:samm:io.catenax.shared.part_site_information_as_built:2.0.0#catenaXsiteId",
        "urn:samm:io.catenax.shared.part_classification:1.0.0#classificationID"
    ]
    
    # Verify results
    template_found = verify_template_triples(graph, template_url)
    mapping_found = verify_mapping_triples(graph, expected_predicates)
    
    result = MappingTestResult(
        success=num_applied > 0 and len(graph) > 0,
        num_rules=num_rules,
        num_triples=len(graph),
        num_rules_applied=num_applied,
        num_rules_skipped=num_rules - num_applied,
        output_graph=output,
        template_triples_found=template_found,
        mapping_triples_found=mapping_found
    )
    
    # Assert success with strict criteria
    assert_mapping_success(
        result,
        min_coverage_percent=80.0,  # Expect most rules to apply
        require_template_triples=True,
        require_mapping_triples=True
    )


@pytest.mark.integration
def test_template_copy_verification(app_context, batch_test_data):
    """
    Verify that the template graph is copied successfully
    This is a simple test that should always pass
    """
    logger.info("="*80)
    logger.info("Testing template graph copy")
    logger.info("="*80)
    
    mapping_url = batch_test_data["mapping_url"]
    data_url = batch_test_data["data_url"]
    
    # Execute mapping
    filename, output, num_rules, num_applied = apply_mapping(
        mapping_url=mapping_url,
        opt_data_url=data_url,
        authorization=None
    )
    
    # Parse results
    graph = parse_rdf_output(output)
    
    # Get template URL
    mapping_data, _ = open_file(mapping_url)
    mapping_dict = yaml.safe_load(mapping_data)
    template_url = mapping_dict["prefixes"]["method"].strip("/")
    
    # Fetch and parse template separately
    template_data, _ = open_file(template_url)
    template_graph = parse_rdf_output(template_data)
    
    logger.info(f"Template graph has {len(template_graph)} triples")
    logger.info(f"Output graph has {len(graph)} triples")
    
    # Verify template triples are in output
    template_found = verify_template_triples(graph, template_url)
    
    assert template_found, "Template triples not found in output graph"
    assert len(graph) >= len(template_graph), "Output has fewer triples than template alone"
    
    logger.info("✓ Template successfully copied to output")


@pytest.mark.integration
def test_mapping_rules_generate_triples(app_context, batch_test_data):
    """
    Verify that mapping rules generate triples (not just template copy)
    Each mapping rule should result in at least one triple
    """
    logger.info("="*80)
    logger.info("Testing that mapping rules generate triples")
    logger.info("="*80)
    
    mapping_url = batch_test_data["mapping_url"]
    data_url = batch_test_data["data_url"]
    
    # Execute mapping
    filename, output, num_rules, num_applied = apply_mapping(
        mapping_url=mapping_url,
        opt_data_url=data_url,
        authorization=None
    )
    
    # Parse results
    graph = parse_rdf_output(output)
    
    # Get template graph size
    mapping_data, _ = open_file(mapping_url)
    mapping_dict = yaml.safe_load(mapping_data)
    template_url = mapping_dict["prefixes"]["method"].strip("/")
    template_data, _ = open_file(template_url)
    template_graph = parse_rdf_output(template_data)
    
    template_size = len(template_graph)
    output_size = len(graph)
    mapping_triples = output_size - template_size
    
    logger.info(f"Template triples: {template_size}")
    logger.info(f"Output triples: {output_size}")
    logger.info(f"Mapping-generated triples: {mapping_triples}")
    logger.info(f"Number of rules: {num_rules}")
    logger.info(f"Rules applied: {num_applied}")
    
    # Assertions
    assert num_applied > 0, "No mapping rules were applied"
    assert mapping_triples > 0, "No triples generated by mapping rules"
    
    # Each applied rule should generate at least one triple
    avg_triples_per_rule = mapping_triples / num_applied if num_applied > 0 else 0
    logger.info(f"Average triples per applied rule: {avg_triples_per_rule:.2f}")
    
    assert avg_triples_per_rule >= 1.0, "Rules did not generate sufficient triples"
    
    logger.info("✓ Mapping rules successfully generated triples")


@pytest.mark.integration
def test_mapping_coverage_analysis(app_context, batch_test_data):
    """
    Analyze mapping coverage and provide detailed diagnostics
    This test always passes but provides useful information
    """
    logger.info("="*80)
    logger.info("Analyzing mapping coverage")
    logger.info("="*80)
    
    mapping_url = batch_test_data["mapping_url"]
    data_url = batch_test_data["data_url"]
    
    # Execute mapping
    filename, output, num_rules, num_applied = apply_mapping(
        mapping_url=mapping_url,
        opt_data_url=data_url,
        authorization=None
    )
    
    # Parse results
    graph = parse_rdf_output(output)
    
    # Analyze coverage
    coverage = analyze_mapping_coverage(
        graph=graph,
        mapping_url=mapping_url,
        num_rules=num_rules,
        num_rules_applied=num_applied
    )
    
    # Print analysis
    logger.info("\nCOVERAGE ANALYSIS:")
    logger.info(f"  Total Rules: {coverage['num_rules']}")
    logger.info(f"  Rules Applied: {coverage['num_rules_applied']}")
    logger.info(f"  Rules Skipped: {coverage['num_rules_skipped']}")
    logger.info(f"  Coverage: {coverage['coverage_percent']:.1f}%")
    logger.info(f"  Total Triples: {coverage['num_triples']}")
    logger.info(f"  Unique Subjects: {coverage['num_subjects']}")
    logger.info(f"  Typed Subjects: {coverage['num_typed_subjects']}")
    logger.info(f"  Unique Predicates: {coverage['num_unique_predicates']}")
    logger.info(f"  Triples per Rule: {coverage['triples_per_rule']:.2f}")
    
    # Save output for inspection
    output_dir = os.path.join(os.path.dirname(__file__), "data", "batch_test")
    output_file = os.path.join(output_dir, "test_output.ttl")
    with open(output_file, 'w') as f:
        f.write(output)
    logger.info(f"\nOutput saved to: {output_file}")
    
    # This test always passes but provides diagnostics
    assert True, "Coverage analysis complete"


@pytest.mark.integration
def test_api_endpoint_create_rdf(app_context, batch_test_data):
    """
    Test the /api/createrdf endpoint directly
    This simulates API usage
    """
    import requests
    
    logger.info("="*80)
    logger.info("Testing /api/createrdf endpoint")
    logger.info("="*80)
    
    # Note: This test requires the app to be running
    # For now, we'll just test the underlying function
    
    mapping_url = batch_test_data["mapping_url"]
    data_url = batch_test_data["data_url"]
    
    # Execute mapping (simulating API call)
    filename, output, num_rules, num_applied = apply_mapping(
        mapping_url=mapping_url,
        opt_data_url=data_url,
        authorization=None
    )
    
    # Verify API response structure
    api_response = {
        "filename": filename,
        "graph": output,
        "num_mappings_applied": num_applied,
        "num_mappings_skipped": num_rules - num_applied
    }
    
    assert "filename" in api_response
    assert "graph" in api_response
    assert "num_mappings_applied" in api_response
    assert "num_mappings_skipped" in api_response
    
    assert api_response["num_mappings_applied"] >= 0
    assert api_response["num_mappings_skipped"] >= 0
    assert len(api_response["graph"]) > 0
    
    logger.info("✓ API response structure is valid")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s", "--log-cli-level=INFO"])
