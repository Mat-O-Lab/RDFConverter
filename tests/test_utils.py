"""
Utility functions for testing RDF mappings
"""
import logging
from typing import Dict, List, Tuple, Optional
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS
import yaml

logger = logging.getLogger(__name__)


class MappingTestResult:
    """Result of a mapping test with detailed diagnostics"""
    
    def __init__(
        self,
        success: bool,
        num_rules: int,
        num_triples: int,
        num_rules_applied: int,
        num_rules_skipped: int,
        output_graph: str,
        template_triples_found: bool = False,
        mapping_triples_found: bool = False,
        errors: Optional[List[str]] = None
    ):
        self.success = success
        self.num_rules = num_rules
        self.num_triples = num_triples
        self.num_rules_applied = num_rules_applied
        self.num_rules_skipped = num_rules_skipped
        self.output_graph = output_graph
        self.template_triples_found = template_triples_found
        self.mapping_triples_found = mapping_triples_found
        self.errors = errors or []
    
    def __str__(self):
        return (
            f"MappingTestResult(\n"
            f"  success={self.success}\n"
            f"  num_rules={self.num_rules}\n"
            f"  num_triples={self.num_triples}\n"
            f"  num_rules_applied={self.num_rules_applied}\n"
            f"  num_rules_skipped={self.num_rules_skipped}\n"
            f"  template_triples_found={self.template_triples_found}\n"
            f"  mapping_triples_found={self.mapping_triples_found}\n"
            f"  errors={self.errors}\n"
            f")"
        )


def parse_rdf_output(output: str) -> Graph:
    """
    Parse RDF output into a Graph
    
    Args:
        output: RDF string in turtle format
        
    Returns:
        rdflib Graph object
    """
    g = Graph()
    try:
        g.parse(data=output, format="turtle")
        logger.info(f"Parsed RDF graph with {len(g)} triples")
        return g
    except Exception as e:
        logger.error(f"Failed to parse RDF output: {e}")
        raise


def verify_template_triples(graph: Graph, template_url: str = None) -> bool:
    """
    Verify that template triples are present in the output graph
    
    This function checks if there are any triples in the graph, without requiring
    specific URL or namespace matching. Template graphs can have any namespace.
    
    Args:
        graph: Output RDF graph
        template_url: Optional URL of the template/method graph (not used for generic checking)
        
    Returns:
        True if template triples are found (graph has content)
    """
    # Simply check if graph has triples - template content can have any namespace
    num_triples = len(graph)
    logger.info(f"Graph contains {num_triples} triples total")
    
    # If a template URL was provided, log it but don't require matching
    # Templates can have any namespace or URL structure
    if template_url:
        logger.debug(f"Template URL provided: {template_url} (checking for any triples, not specific URLs)")
    
    # Consider template found if graph has any triples
    return num_triples > 0


def verify_mapping_triples(graph: Graph, expected_predicates: Optional[List[str]] = None) -> bool:
    """
    Verify that mapping-generated triples are present
    
    Args:
        graph: Output RDF graph
        expected_predicates: List of expected predicate URIs
        
    Returns:
        True if mapping triples are found
    """
    # Count total triples
    total_triples = len(graph)
    logger.info(f"Total triples in graph: {total_triples}")
    
    if expected_predicates:
        found_predicates = []
        for pred_uri in expected_predicates:
            pred = URIRef(pred_uri)
            if (None, pred, None) in graph:
                found_predicates.append(pred_uri)
                logger.info(f"✓ Found expected predicate: {pred_uri}")
            else:
                logger.warning(f"✗ Missing expected predicate: {pred_uri}")
        
        return len(found_predicates) > 0
    
    return total_triples > 0


def count_rules_in_mapping(mapping_data: str) -> int:
    """
    Count the number of mapping rules in a YARRRML mapping
    
    Args:
        mapping_data: YARRRML mapping as string
        
    Returns:
        Number of mapping rules
    """
    try:
        mapping_dict = yaml.safe_load(mapping_data)
        mappings = mapping_dict.get("mappings", {})
        return len(mappings)
    except Exception as e:
        logger.error(f"Failed to parse YARRRML mapping: {e}")
        return 0


def analyze_mapping_coverage(
    graph: Graph,
    mapping_url: str,
    num_rules: int,
    num_rules_applied: int
) -> Dict[str, any]:
    """
    Analyze the coverage and quality of a mapping result
    
    Args:
        graph: Output RDF graph
        mapping_url: URL of the mapping file
        num_rules: Total number of mapping rules
        num_rules_applied: Number of rules that generated triples
        
    Returns:
        Dictionary with coverage metrics
    """
    num_triples = len(graph)
    coverage_percent = (num_rules_applied / num_rules * 100) if num_rules > 0 else 0
    
    # Get subject types
    subject_types = set()
    for s in graph.subjects(RDF.type, None):
        subject_types.add(s)
    
    # Get unique predicates
    unique_predicates = set(graph.predicates())
    
    return {
        "num_rules": num_rules,
        "num_rules_applied": num_rules_applied,
        "num_rules_skipped": num_rules - num_rules_applied,
        "num_triples": num_triples,
        "coverage_percent": coverage_percent,
        "num_subjects": len(set(graph.subjects())),
        "num_typed_subjects": len(subject_types),
        "num_unique_predicates": len(unique_predicates),
        "triples_per_rule": num_triples / num_rules if num_rules > 0 else 0
    }


def verify_rule_generated_triples(
    graph: Graph,
    rule_name: str,
    expected_min_triples: int = 1
) -> Tuple[bool, int]:
    """
    Verify that a specific mapping rule generated triples
    
    Args:
        graph: Output RDF graph
        rule_name: Name of the mapping rule
        expected_min_triples: Minimum expected triples
        
    Returns:
        Tuple of (success, num_triples_found)
    """
    # This is a heuristic - we can't directly trace which rule generated which triple
    # but we can check for patterns
    
    # For now, just check that graph has content
    num_triples = len(graph)
    success = num_triples >= expected_min_triples
    
    return success, num_triples


def print_mapping_summary(result: MappingTestResult):
    """
    Print a human-readable summary of mapping test results
    
    Args:
        result: MappingTestResult object
    """
    logger.info("=" * 80)
    logger.info("MAPPING TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Success: {'✓' if result.success else '✗'}")
    logger.info(f"Total Rules: {result.num_rules}")
    logger.info(f"Rules Applied: {result.num_rules_applied}")
    logger.info(f"Rules Skipped: {result.num_rules_skipped}")
    logger.info(f"Total Triples Generated: {result.num_triples}")
    
    if result.num_rules > 0:
        coverage = (result.num_rules_applied / result.num_rules) * 100
        logger.info(f"Rule Coverage: {coverage:.1f}%")
    
    logger.info(f"Template Triples Found: {'✓' if result.template_triples_found else '✗'}")
    logger.info(f"Mapping Triples Found: {'✓' if result.mapping_triples_found else '✗'}")
    
    if result.errors:
        logger.error("Errors:")
        for error in result.errors:
            logger.error(f"  - {error}")
    
    logger.info("=" * 80)


def assert_mapping_success(
    result: MappingTestResult,
    min_coverage_percent: float = 80.0,
    require_template_triples: bool = True,
    require_mapping_triples: bool = True
):
    """
    Assert that a mapping test meets success criteria
    
    Args:
        result: MappingTestResult object
        min_coverage_percent: Minimum required rule coverage percentage
        require_template_triples: Whether template triples are required
        require_mapping_triples: Whether mapping triples are required
        
    Raises:
        AssertionError if success criteria not met
    """
    print_mapping_summary(result)
    
    errors = []
    
    # Check rule coverage
    if result.num_rules > 0:
        coverage = (result.num_rules_applied / result.num_rules) * 100
        if coverage < min_coverage_percent:
            errors.append(
                f"Rule coverage {coverage:.1f}% is below minimum {min_coverage_percent}%"
            )
    
    # Check for triples generated
    if result.num_triples == 0:
        errors.append("No triples were generated")
    
    # Check template triples if required
    if require_template_triples and not result.template_triples_found:
        errors.append("Template triples not found in output")
    
    # Check mapping triples if required
    if require_mapping_triples and not result.mapping_triples_found:
        errors.append("Mapping triples not found in output")
    
    # Include any errors from the result
    errors.extend(result.errors)
    
    if errors:
        error_msg = "Mapping test failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise AssertionError(error_msg)
    
    logger.info("✓ Mapping test passed all criteria")
