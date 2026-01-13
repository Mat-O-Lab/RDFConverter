# Batch Mapping Test - Debugging JSONPath with Plain JSON

## Issue
JSONPath-based YARRRML mappings with plain JSON data sources are not generating any triples, even though the same mapping works in YARRRML web apps.

## Test Setup

### Files Created
1. `tests/data/batch_test/batch_mapping.yaml` - YARRRML mapping configuration
2. `tests/data/batch_test/batch_data.json` - Test JSON data
3. `tests/test_batch_mapping.py` - Debug test script

### Enhanced Logging
Added detailed debug logging to `app.py` in the `apply_mapping` function to trace:
- Whether data is detected as RDF or plain JSON
- What data is being sent to the RML mapper
- RML mapper response status and output

## Running the Test

### Prerequisites
The application requires two microservices to be running:
1. **YARRRML Parser** - Converts YARRRML to RML rules
2. **RML Mapper** - Executes RML rules on data

### Option 1: Run with Docker Compose (Recommended)
```bash
# Start the services
docker-compose up -d

# Wait for services to be ready (check logs)
docker-compose logs -f

# Set environment variables for the test
export YARRRML_URL="http://localhost:3001"
export MAPPER_URL="http://localhost:4000"

# Run the test
cd /home/hanke/RDFConverter
python tests/test_batch_mapping.py
```

### Option 2: Run Services Individually
```bash
# Terminal 1: Start YARRRML Parser
docker run -p 3001:3001 -e PORT=3001 ghcr.io/mat-o-lab/yarrrml-parser:v.1.0.2

# Terminal 2: Start RML Mapper
docker run -p 4000:4000 -e PORT=4000 ghcr.io/mat-o-lab/rmlmapper-webapi:latest

# Terminal 3: Run test
export YARRRML_URL="http://localhost:3001"
export MAPPER_URL="http://localhost:4000"
python tests/test_batch_mapping.py
```

## Expected Output

The test script will:
1. Load the mapping and data files
2. Call `apply_mapping()` with debug logging enabled
3. Display:
   - Number of rules possible vs applied
   - Generated RDF output
   - Detailed debug information about each step

### Success Scenario
```
Number of rules possible: 11
Number of rules applied: 11 (or close to it)
Generated RDF output with triples
```

### Failure Scenario (Current Issue)
```
Number of rules possible: 11
Number of rules applied: 0
NO TRIPLES GENERATED!
```

## Debug Output Location

- Console: Real-time debug output
- File: `debug_batch_mapping.log` - Complete debug trace
- Output file: `tests/data/batch_test/output.ttl` - Generated RDF (if any)

## What to Look For in Debug Output

1. **Is data detected as plain JSON?**
   - Should see: `"Data is plain JSON, will be processed by RML mapper only"`

2. **What is sent to RML mapper?**
   - Check the "DATA BEING SENT TO RML MAPPER" section
   - Verify `is_rdf_data: False`
   - Check data content format

3. **RML Mapper response**
   - Status code (should be 200)
   - Output length
   - Any error messages

4. **Potential Issues to Identify**
   - Data format mismatch (JSON encoding issues)
   - RML rules source references incorrect
   - RML mapper doesn't support JSONPath properly
   - Iterator expressions not matching JSON structure

## Next Steps After Running Test

Based on debug output, we may need to:
1. Adjust how plain JSON is sent to RML mapper
2. Fix source name replacement in RML rules
3. Modify iterator expressions in the mapping
4. Check RML mapper configuration/compatibility
