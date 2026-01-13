"""
Test script to debug JSONPath mapping issue with plain JSON data
"""
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import apply_mapping

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('debug_batch_mapping.log')
    ]
)

logger = logging.getLogger(__name__)

def test_batch_mapping():
    """Test the batch mapping with local files"""
    
    # Use file:// URLs for local testing
    current_dir = os.path.dirname(os.path.abspath(__file__))
    mapping_url = f"file://{current_dir}/data/batch_test/batch_mapping.yaml"
    data_url = f"file://{current_dir}/data/batch_test/batch_data.json"
    
    logger.info("="*80)
    logger.info("Starting batch mapping test")
    logger.info(f"Mapping URL: {mapping_url}")
    logger.info(f"Data URL: {data_url}")
    logger.info("="*80)
    
    try:
        filename, output, num_possible, num_applied = apply_mapping(
            mapping_url=mapping_url,
            opt_data_url=data_url,
            authorization=None
        )
        
        logger.info("="*80)
        logger.info("RESULTS:")
        logger.info(f"Output filename: {filename}")
        logger.info(f"Number of rules possible: {num_possible}")
        logger.info(f"Number of rules applied: {num_applied}")
        logger.info(f"Number of rules skipped: {num_possible - num_applied}")
        logger.info("="*80)
        logger.info("Generated RDF output:")
        logger.info(output)
        logger.info("="*80)
        
        # Save output to file
        output_file = os.path.join(current_dir, "data/batch_test/output.ttl")
        with open(output_file, 'w') as f:
            f.write(output)
        logger.info(f"Output saved to: {output_file}")
        
        if num_applied == 0:
            logger.error("NO TRIPLES GENERATED! This is the issue we need to debug.")
            return False
        else:
            logger.info(f"SUCCESS: {num_applied} triples generated")
            return True
            
    except Exception as e:
        logger.error(f"Error during mapping: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("Starting batch mapping debug test")
    success = test_batch_mapping()
    sys.exit(0 if success else 1)
