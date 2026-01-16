# RDFConverter

[![Publish Docker image](https://github.com/Mat-O-Lab/RDFConverter/actions/workflows/PublishContainer.yml/badge.svg?branch=main&event=workflow_dispatch)](https://github.com/Mat-O-Lab/RDFConverter/actions/workflows/PublishContainer.yml) [![TestExamples](https://github.com/Mat-O-Lab/RDFConverter/actions/workflows/TestExamples.yml/badge.svg?branch=main)](https://github.com/Mat-O-Lab/RDFConverter/actions/workflows/TestExamples.yml)

**Transform your data into semantic, machine-readable knowledge graphs - no coding required.**

🌐 **Demo:** http://rdfconverter.matolab.org/

---

## Why RDFConverter?

RDFConverter bridges the gap between raw data (JSON, CSV, RDF) and standardized semantic ontologies using declarative YARRRML mappings. Whether you're publishing FAIR research data, integrating legacy systems, or implementing industry standards like Catena-X, RDFConverter makes semantic data transformation simple and maintainable.

### Key Benefits

- ✅ **Declarative Mappings** - Use human-readable YARRRML instead of imperative code
- ✅ **Template-Based** - Reuse semantic method templates across datasets
- ✅ **Industry Standards** - Built-in support for CSVW, SAMM, PROV-O
- ✅ **Multi-Format** - JSON, CSV, RDF/Turtle, JSON-LD - all work seamlessly
- ✅ **Validation Built-In** - SHACL shapes ensure data quality
- ✅ **Production-Ready** - RESTful API, Docker deployment, CI/CD tested
- ✅ **Provenance Tracking** - Automatic PROV-O metadata generation

### What Makes RDFConverter Different?

RDFConverter doesn't reinvent YARRRML or RML - it packages the official tools ([yarrrml-parser](https://github.com/RMLio/yarrrml-parser), [rmlmapper-java](https://github.com/RMLio/rmlmapper-java)) into a production-ready containerized service with a REST API.

**✅ With RDFConverter:**
- `docker compose up` - Done! No dependency installation needed
- Call from any language via REST API (Python, R, JavaScript, curl, etc.)
- Pre-configured for production (logging, error handling, provenance)
- Built-in testing and validation endpoints
- Works on any OS (Linux, Mac, Windows)

**📦 Without RDFConverter (Manual Setup):**
- Install Node.js for yarrrml-parser
- Install Java for RML Mapper
- Configure both tools separately
- Write glue code to connect them
- Handle errors and edge cases yourself
- Set up logging and monitoring

**For full YARRRML/RML capabilities**, see:
- [YARRRML Specification](https://rml.io/yarrrml/spec/)
- [RML Specification](https://rml.io/specs/rml/)
- [RML.io Documentation](https://rml.io/)

---

## Quick Start

### Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose installed and running
- Ports 3001, 4000, and 6003 available

### 5-Minute Setup

```bash
# 1. Clone the repository
git clone https://github.com/Mat-O-Lab/RDFConverter.git
cd RDFConverter

# 2. Create configuration
cat > .env << EOF
PARSER_PORT=3001
MAPPER_PORT=4000
APP_PORT=6003
CONVERTER_PORT=5000
YARRRML_URL=http://yarrrml-parser:3001
MAPPER_URL=http://rmlmapper:4000
APP_MODE=development
SSL_VERIFY=True
EOF

# 3. Launch services
docker compose -f docker-compose.develop.yml up -d

# 4. Wait for services to start (30 seconds)
sleep 30

# 5. Access the application
# Web UI: http://localhost:6003/
# API docs: http://localhost:6003/api/docs
```

### Your First Mapping (2 Minutes)

Test the example CSVW mapping that transforms tensile test data:

```bash
curl -X POST http://localhost:6003/api/createrdf \
  -H "Content-Type: application/json" \
  -d '{"mapping_url":"https://github.com/Mat-O-Lab/RDFConverter/raw/main/examples/csvw-template-map.yaml"}'
```

You'll get back a JSON response with:
- `graph`: The generated RDF/Turtle output
- `num_mappings_applied`: Number of successful mapping rules
- `num_mappings_skipped`: Rules that didn't match data

---

## Real-World Use Cases

### Use Case 1: Materials Testing Laboratory

**Challenge:** Laboratory generates CSV data from tensile testing machines. Data needs to be FAIR (Findable, Accessible, Interoperable, Reusable) and comply with DIN EN ISO 527-3 standard.

**Solution:** Use `csvw-template-map.yaml` to map CSV data to the MSEO (Materials Science and Engineering Ontology) using a standardized method template.

**Result:**
- Raw CSV becomes semantic RDF
- Data structured according to ISO standard
- Template ensures consistency across all tests
- Other researchers can understand and reuse the data

📁 **See:** [`examples/csvw-template-map.yaml`](examples/csvw-template-map.yaml)

---

### Use Case 2: Automotive Supply Chain (Catena-X)

**Challenge:** Automotive partners in the Catena-X data space need to exchange batch manufacturing data in a standardized, interoperable format.

**Solution:** Use `catenax-batch-map.yaml` to transform JSON batch payloads into SAMM (Semantic Aspect Meta Model) compliant RDF that references the official io.catenax.batch:3.0.1 specification.

**Result:**
- JSON payloads become semantic documents
- Full compliance with Catena-X standards
- Traceability across supply chain partners
- Automated validation against SAMM models

📁 **See:** [`examples/catenax-batch-map.yaml`](examples/catenax-batch-map.yaml)

---

### Use Case 3: Your Use Case

**Have JSON/CSV/RDF data that needs semantic structure?**

1. Identify your data source format
2. Find or create an ontology/template
3. Write a YARRRML mapping (see examples)
4. Test with RDFConverter
5. Deploy and share!

---

## Comparison: Different Approaches

| Approach | Setup Time | Use Case | Best For |
|----------|------------|----------|----------|
| **RDFConverter** | 5 minutes | Reusable workflows, teams, production | Declarative mappings + REST API |
| SPARQL CONSTRUCT | Immediate | One-off transformations | Already know SPARQL, simple transforms |
| Custom Scripts | Varies | Complex custom logic | Unique requirements, performance critical |
| GUI Tools (e.g., OntoRefine) | Minutes | Visual mapping | Non-developers, exploratory work |

**Note:** All approaches have their place. RDFConverter excels when you need maintainable, version-controlled mappings exposed via API.

---

## Frequently Asked Questions

**Q: What transformations can RDFConverter handle?**
A: Any transformation supported by [YARRRML/RML](https://rml.io/yarrrml/spec/), including:
- CSV/JSON/XML to RDF
- RDF to RDF (vocabulary transformation)
- Complex joins and conditions
- Nested data structures
- Functions and data manipulation

**Q: Can I transform between different RDF vocabularies?**
A: Yes! Use RDF as your data source in YARRRML mappings to map from one vocabulary to another (e.g., Dublin Core → Schema.org). See [RML.io examples](https://rml.io/specs/rml/#example-rdf) for RDF source handling.

**Q: Does my data leave my server?**
A: No. All processing is local. RDFConverter only fetches URLs you provide in mappings.

**Q: Can I use this in air-gapped/offline environments?**
A: Yes, once Docker images are pulled. No internet required for processing.

**Q: How do I learn YARRRML syntax?**
A: See [YARRRML Tutorial](https://rml.io/yarrrml/tutorial/) and try [YARRRML Matey](https://rml.io/yarrrml/matey/) online editor.

**Q: What about performance for large datasets?**
A: Performance depends on the underlying RML Mapper (Java). For specifics, see [RML Mapper documentation](https://github.com/RMLio/rmlmapper-java).

**Q: Can I integrate this into my Python/R/Node.js workflow?**
A: Yes! Use the REST API from any language that can make HTTP requests. See examples in the API Reference section.

---

## How It Works

RDFConverter uses a simple 3-step process:

```
┌─────────────────────────────────────┐
│  1. Define Mapping (YARRRML)        │
│  - Specify data sources             │
│  - Define transformation rules      │
│  - Optional: reference templates    │
└─────────────────┬───────────────────┘
                  ↓
┌─────────────────────────────────────┐
│  2. RDFConverter Processes          │
│  - Converts YARRRML → RML           │
│  - Applies rules to your data       │
│  - Merges with templates (optional) │
│  - Validates output (optional)      │
└─────────────────┬───────────────────┘
                  ↓
┌─────────────────────────────────────┐
│  3. Get Semantic RDF                │
│  - Structured knowledge graph       │
│  - Validated against schemas        │
│  - Provenance metadata included     │
└─────────────────────────────────────┘
```

---

## Supported Data Formats

### Native RML Reference Formulations

RDFConverter supports all standard RML reference formulations as defined in the [RML specification](https://rml.io/specs/rml/):

| Format | MIME Type | Reference Formulation | Iterator Syntax | Example |
|--------|-----------|----------------------|-----------------|---------|
| CSV | text/plain | `csv` | N/A (column names) | `$(columnName)` |
| JSON | application/json | `jsonpath` | `$.path.to[*].data` | `$..items[*]` |
| XML | application/xml | `xpath` | `/path/to/element` | `//book[@id]` |
| XML | application/xml | `xquery` | XQuery expressions | `for $x in ...` |

### Enhanced RDF Support 🎯

**RDFConverter automatically converts RDF formats to JSON-LD**, enabling JSONPath-based mappings on semantic data sources. This is a key differentiator that allows you to use existing RDF/Turtle data with the powerful JSONPath iterator syntax.

| Input Format | File Extension | Conversion | Use With |
|--------------|----------------|------------|----------|
| Turtle | .ttl | → JSON-LD | `referenceFormulation: jsonpath` |
| RDF/XML | .rdf, .owl | → JSON-LD | `referenceFormulation: jsonpath` |
| N-Triples | .nt | → JSON-LD | `referenceFormulation: jsonpath` |
| N3 | .n3 | → JSON-LD | `referenceFormulation: jsonpath` |
| JSON-LD | .jsonld | Preserved | `referenceFormulation: jsonpath` |

#### How RDF Conversion Works

The conversion process is transparent and automatic:

1. **Detection:** RDFConverter detects RDF formats using file extension and content analysis
2. **Parsing:** Loads RDF data with RDFLib into an in-memory graph
3. **Namespace Preservation:** Extracts and preserves prefix bindings from original data
4. **JSON-LD Serialization:** Converts graph to JSON-LD with standard `@context` for CSVW
5. **Mapping Execution:** RML Mapper processes the JSON-LD using JSONPath iterators

**Processing Pipeline:**
```
Turtle/RDF File → RDFLib Parser → Graph → JSON-LD Serializer →
JSON-LD with @context → RML Mapper + JSONPath → Output RDF
```

#### Example: Using Turtle Data with JSONPath

Suppose you have a Turtle file `data.ttl`:

```turtle
@prefix csvw: <http://www.w3.org/ns/csvw#> .
@prefix ex: <http://example.org/> .

ex:table a csvw:Table ;
    csvw:column ex:col1, ex:col2 .

ex:col1 a csvw:Column ;
    csvw:name "Force" ;
    csvw:datatype "number" .

ex:col2 a csvw:Column ;
    csvw:name "Displacement" ;
    csvw:datatype "number" .
```

**YARRRML Mapping:**
```yaml
prefixes:
  csvw: 'http://www.w3.org/ns/csvw#'
  ex: 'http://example.org/'

sources:
  columns:
    access: 'https://example.com/data.ttl'    # ← Turtle file
    iterator: '$.[?(@.type=="csvw:Column")]'  # ← JSONPath on JSON-LD
    referenceFormulation: jsonpath             # ← Use JSONPath

mappings:
  ColumnMapping:
    sources: [columns]
    s: ex:measurement_$(["csvw:name"])
    po:
      - [rdf:type, ex:Measurement]
      - [ex:columnName, $(["csvw:name"])]
      - [ex:dataType, $(["csvw:datatype"])]
```

**What Happens Behind the Scenes:**

1. RDFConverter downloads `data.ttl` (Turtle format)
2. Converts to JSON-LD:
   ```json
   {
     "@context": {
       "csvw": "http://www.w3.org/ns/csvw#",
       "ex": "http://example.org/"
     },
     "@graph": [
       {
         "@id": "ex:col1",
         "@type": "csvw:Column",
         "csvw:name": "Force",
         "csvw:datatype": "number"
       },
       {
         "@id": "ex:col2",
         "@type": "csvw:Column",
         "csvw:name": "Displacement",
         "csvw:datatype": "number"
       }
     ]
   }
   ```
3. RML Mapper applies JSONPath iterator: `$.[?(@.type=="csvw:Column")]`
4. Generates output RDF with mappings applied

#### Example: CSVW Metadata (JSON-LD)

The existing `csvw-template-map.yaml` example demonstrates this perfectly - it uses CSVW metadata (which is JSON-LD) with JSONPath iterators:

```yaml
sources:
  columns:
    access: 'https://.../example-metadata.json'
    iterator: '$..columns[*]'        # JSONPath on JSON-LD structure
    referenceFormulation: jsonpath
  annotations:
    access: 'https://.../example-metadata.json'
    iterator: '$.notes[*]'           # Another JSONPath iterator
    referenceFormulation: jsonpath
```

This works seamlessly because:
- CSVW metadata is already JSON-LD
- RDFConverter preserves the `@context`
- JSONPath can navigate the nested JSON structure
- RML Mapper generates semantic RDF output

### Limitations and Constraints

#### ❌ What's NOT Supported

**Direct RDF/Turtle reference formulation:**
```yaml
# ❌ This does NOT work:
sources:
  data:
    access: 'https://example.com/data.ttl'
    referenceFormulation: turtle  # ❌ Not supported by RML Mapper
```

**Why?** The underlying RML Mapper (Java implementation) does not support `referenceFormulation: turtle` or other RDF formats as iterators. RDF formats don't have a natural "iteration" concept like arrays in JSON or rows in CSV.

#### ✅ What to Use Instead

**Use automatic JSON-LD conversion with JSONPath:**
```yaml
# ✅ This DOES work:
sources:
  data:
    access: 'https://example.com/data.ttl'  # ✅ Auto-converted to JSON-LD
    referenceFormulation: jsonpath          # ✅ Use JSONPath
    iterator: '$'                           # ✅ Iterate over JSON-LD structure
```

**For complex RDF queries:** If you need SPARQL-like pattern matching, consider:
1. Pre-processing RDF with SPARQL CONSTRUCT queries
2. Using the resulting RDF as your data source
3. Or restructuring your mapping to work with JSON-LD's hierarchical structure

### Best Practices

**✅ DO:**
- Use JSONPath for all data sources (JSON, JSON-LD, auto-converted RDF)
- Leverage automatic RDF → JSON-LD conversion for semantic sources
- Test with `/api/test` endpoint to verify iterator expressions
- Check the JSON-LD structure if mappings don't match (use debug mode)

**❌ DON'T:**
- Try to use `referenceFormulation: turtle` (not supported)
- Assume RDF structure will directly map to JSON arrays (test first)
- Mix reference formulations in a single source definition

---

## Architecture & Components

### Microservices Architecture

RDFConverter consists of three Docker containers:

- **RDFConverter** (FastAPI, Python) - Main orchestrator and API
- **YARRRML Parser** (Node.js) - Converts human-readable YARRRML to machine-readable RML
- **RML Mapper** (Java) - Executes RML mapping rules on data

### Core Technologies

- **[YARRRML](https://rml.io/yarrrml/)** - Human-friendly RDF mapping language
- **[RML](https://rml.io/)** - RDF Mapping Language (W3C standard)
- **[RDFLib](https://rdflib.readthedocs.io/)** - Python library for RDF processing
- **[PySHACL](https://github.com/RDFLib/pySHACL)** - SHACL constraint validation
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern Python web framework with OpenAPI

---

## API Reference

### Core Endpoints

| Endpoint | Method | Purpose | Input | Output |
|----------|--------|---------|-------|--------|
| `/api/yarrrmltorml` | POST | Convert YARRRML to RML | YARRRML file URL | RML (Turtle format) |
| `/api/createrdf` | POST | Execute mapping and generate RDF | Mapping URL + optional data URL | RDF graph + statistics |
| `/api/checkmapping` | POST | Test mapping applicability | Mapping URL + data URL | Rule coverage report |
| `/api/rdfvalidator` | POST | Validate RDF against SHACL | RDF URL + SHACL shapes URL | Validation report |
| `/api/test` | POST | Test mapping with detailed stats | Mapping URL + optional data URL | Per-rule statistics |
| `/api/docs` | GET | Interactive API documentation | - | Swagger UI |

### Example API Call

```bash
# Execute a mapping
curl -X POST http://localhost:6003/api/createrdf \
  -H "Content-Type: application/json" \
  -d '{
    "mapping_url": "https://example.com/my-mapping.yaml",
    "data_url": "https://example.com/my-data.json"
  }'
```

**Response:**
```json
{
  "filename": "my-data-joined.ttl",
  "graph": "@prefix ex: <http://example.org/> .\n...",
  "num_mappings_applied": 7,
  "num_mappings_skipped": 0
}
```

### Test Endpoint for Development

The `/api/test` endpoint is particularly useful during development:

```bash
curl -X POST "http://localhost:6003/api/test" \
  -H "Content-Type: application/json" \
  -d '{"mapping_url":"https://github.com/Mat-O-Lab/RDFConverter/raw/main/examples/csvw-template-map.yaml"}'
```

Returns detailed statistics:
- Total rules vs. applied rules
- Per-rule triple counts
- Subject coverage
- Individual rule outputs
- Processing logs

---

## Example Mappings Deep Dive

### Example 1: `csvw-template-map.yaml` - Template-Based Semantic Mapping

**What it does:**
Transforms CSV tensile test data with CSVW metadata into a semantic knowledge graph structured according to the DIN EN ISO 527-3 standard using the MSEO (Materials Science and Engineering Ontology).

**Key Features Demonstrated:**

1. **Multiple Data Sources from CSVW:**
```yaml
sources:
  columns:
    access: 'https://.../example-metadata.json'
    iterator: '$..columns[*]'     # Iterate over CSV columns
    referenceFormulation: jsonpath
  annotations:
    access: 'https://.../example-metadata.json'
    iterator: '$.notes[*]'        # Iterate over metadata notes
    referenceFormulation: jsonpath
```

2. **Template Graph Usage:**
```yaml
prefixes:
  template: 'https://.../DIN_EN_ISO_527-3.drawio.ttl/'
```
The template provides a pre-structured semantic representation of the testing method. Individual measurements are linked to template placeholders.

3. **Conditional Mappings:**
```yaml
mappings:
  SpecimenID:
    sources: [annotations]
    condition:
      function: equal
      parameters:
      - [str1, $(label)]
      - [str2, "aktuelle Probe"]  # Match German label
    po:
    - ['http://purl.obolibrary.org/obo/RO_0010002', 'template:SpecimenID~iri']
```
Rules only apply when conditions match, enabling flexible data extraction.

**Why this matters:**

- **Reusability:** Same template works for all DIN EN ISO 527-3 tests
- **Standardization:** Data follows established ontology (MSEO)
- **Interoperability:** Other labs using the same standard can understand your data
- **FAIR Data:** Findable, Accessible, Interoperable, Reusable

**Data Flow:**
```
CSV file → CSVW metadata (JSON-LD) → YARRRML rules →
Template graph + Mapped data → Validated semantic RDF
```

---

### Example 2: `catenax-batch-map.yaml` - Industry Standard Transformation

**What it does:**
Transforms Catena-X batch manufacturing data (JSON format) into a semantic RDF document that conforms to the SAMM (Semantic Aspect Meta Model) batch specification version 3.0.1.

**Key Features Demonstrated:**

1. **Multiple Iterators for Complex JSON:**
```yaml
sources:
  root:
    access: 'https://.../Batch.json'
    iterator: '$'                          # Root object
  identifiers:
    iterator: '$.localIdentifiers[*]'      # Array of identifiers
  sites_items:
    iterator: '$.manufacturingInformation.sites[*]'  # Nested array
  partClass_items:
    iterator: '$.partTypeInformation.partClassification[*]'
```

2. **Industry-Standard Namespace Prefixes:**
```yaml
prefixes:
  cx: "urn:samm:io.catenax.batch:3.0.1#"
  samm: "urn:samm:org.eclipse.esmf.samm:meta-model:2.3.0#"
  ext-built: "urn:samm:io.catenax.shared.part_site_information_as_built:2.0.0#"
  ext-classification: "urn:samm:io.catenax.shared.part_classification:1.0.0#"
```

3. **Nested Object Mappings:**
```yaml
mappings:
  batch:
    source: [root]
    s: urn-uuid:$(catenaXId)
    po:
      - [rdf:type, cx:Batch]
      - [cx:catenaXId, $(catenaXId)]
      - p: cx:localIdentifiers
        o:
          mapping: identifiers_list  # Links to another mapping
          condition:
            function: equal
            parameters: [[str1, "1"], [str2, "1"]]
```

4. **Reference to External Semantic Model:**
```yaml
prefixes:
  method: "https://.../io.catenax.batch/3.0.1/Batch.ttl/"
```
The mapping references the official Catena-X batch semantic model, ensuring compliance.

**Why this matters:**

- **Industry Compliance:** Meets Catena-X data space requirements
- **Supply Chain Traceability:** Enables end-to-end batch tracking across partners
- **Semantic Interoperability:** Different systems from different vendors can exchange data
- **Automated Validation:** Output can be validated against SAMM models
- **Scalability:** Same pattern works for other Catena-X aspects (SerialPart, JustInSequencePart, etc.)

**Data Flow:**
```
Catena-X JSON payload → YARRRML rules →
SAMM batch model reference → Compliant semantic RDF
```

**Real-World Application:**
In the automotive industry, this enables a battery manufacturer to provide semantic batch data to the OEM, who can then trace that batch through the entire vehicle lifecycle - all while maintaining data sovereignty and interoperability.

---

## Testing & CI/CD

### Automated Testing

RDFConverter uses GitHub Actions to automatically test all example mappings on every push:

1. **Workflow Location:** `.github/workflows/TestExamples.yml`
2. **Tests Both Endpoints:**
   - `/api/yarrrmltorml` - Generates `.rml` files
   - `/api/createrdf` - Generates `.rdf` files
3. **Commit Results:** Generated outputs are committed back to `examples/` for review
4. **Test on Push:** Runs on all pushes to `main` or `develop` branches

### Run Tests Locally

**Via API Endpoint:**
```bash
# Test a specific mapping
curl -X POST "http://localhost:6003/api/test?mapping_url=https://github.com/Mat-O-Lab/RDFConverter/raw/main/examples/csvw-template-map.yaml"
```

**Test Your Own Mapping:**
1. Add your `.yaml` file to the `examples/` directory
2. Commit and push to GitHub
3. GitHub Actions automatically tests it
4. Review generated `.rml` and `.rdf` files in the commit

### Test Results

The test endpoint provides detailed statistics:

```json
{
  "success": true,
  "num_rules_total": 7,
  "num_rules_applied": 7,
  "num_rules_skipped": 0,
  "num_triples_generated": 156,
  "rule_statistics": [
    {
      "rule_name": "SpecimenID",
      "predicate": "http://purl.obolibrary.org/obo/RO_0010002",
      "triples_generated": 1,
      "subjects_affected": 1
    },
    ...
  ]
}
```

---

## Deployment

### Development Mode

For local development with hot-reloading:

```bash
docker compose -f docker-compose.develop.yml up -d
```

Access at: http://localhost:6003

### Production Mode

For production deployment:

```bash
docker compose up -d
```

Or use pre-built images from GitHub Container Registry:

```yaml
services:
  rdfconverter:
    image: ghcr.io/mat-o-lab/rdfconverter:latest
  yarrrml-parser:
    image: ghcr.io/mat-o-lab/yarrrml-parser:latest
  rmlmapper:
    image: ghcr.io/mat-o-lab/rmlmapper-webapi:latest
```

### Environment Variables

Configure via `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_PORT` | External port for RDFConverter API | 6003 |
| `CONVERTER_PORT` | Internal container port | 5000 |
| `PARSER_PORT` | YARRRML Parser port | 3001 |
| `MAPPER_PORT` | RML Mapper port | 4000 |
| `APP_MODE` | "development" or "production" | production |
| `SSL_VERIFY` | Verify SSL certificates | True |
| `YARRRML_URL` | Internal URL to YARRRML Parser | http://yarrrml-parser:3001 |
| `MAPPER_URL` | Internal URL to RML Mapper | http://rmlmapper:4000 |

---

## Creating Your Own Mapping

### Step-by-Step Guide

1. **Identify Your Data Source**
   - JSON file (plain or JSON-LD)
   - CSV with CSVW metadata
   - Existing RDF (Turtle, RDF/XML, etc.)

2. **Choose or Create a Semantic Template (Optional)**
   - Look for existing ontologies in your domain
   - Create a template RDF file with placeholders
   - Reference the template URL in your mapping

3. **Write YARRRML Mapping**

   Basic structure:
   ```yaml
   prefixes:
     ex: "http://example.org/"
     template: "http://example.org/template/"  # Optional

   base: "http://example.org/data/"

   sources:
     mydata:
       access: "https://example.com/data.json"
       iterator: "$"
       referenceFormulation: jsonpath

   mappings:
     MyMapping:
       sources: [mydata]
       s: ex:$(id)
       po:
         - [rdf:type, ex:MyClass]
         - [ex:property, $(value)]
   ```

4. **Test Your Mapping**
   ```bash
   curl -X POST http://localhost:6003/api/test \
     -H "Content-Type: application/json" \
     -d '{"mapping_url":"https://example.com/my-mapping.yaml"}'
   ```

5. **Iterate**
   - Check `num_rules_applied` vs `num_rules_skipped`
   - Review per-rule statistics
   - Adjust conditions and mappings
   - Test again

6. **Deploy**
   - Add to your production workflow
   - Set up automated validation if needed
   - Monitor mapping success rates

### Resources

- **[YARRRML Tutorial](https://rml.io/yarrrml/tutorial/)** - Learn YARRRML syntax
- **[RML Specification](https://rml.io/specs/rml/)** - Detailed RML reference
- **Example Mappings** - See `examples/` directory for real-world examples
- **[YARRRML Matey](https://rml.io/yarrrml/matey/)** - Online YARRRML editor

---

## Troubleshooting

### Common Issues

**Docker not running**
```
Error: Cannot connect to the Docker daemon
```
→ Start Docker and try again

**Port already in use**
```
Error: bind: address already in use
```
→ Change ports in `.env` file or stop conflicting services

**No triples generated**
```json
{"num_mappings_applied": 0, "num_mappings_skipped": 7}
```
→ Check:
- Data source URL is accessible
- Mapping conditions match your data
- Use `/api/test` endpoint for detailed diagnostics

**YARRRML syntax error**
```
Could not read mapping file - is it valid YAML format?
```
→ Validate YAML syntax at https://www.yamllint.com/

**Services not starting**
```bash
# Check service status
docker compose ps

# View logs
docker compose logs rdfconverter
docker compose logs yarrrml-parser
docker compose logs rmlmapper

# Restart services
docker compose restart
```

### Debug Mode

Enable detailed logging:

```bash
# Set in .env
APP_MODE=development

# Restart services
docker compose restart rdfconverter
```

View logs in real-time:
```bash
docker compose logs -f rdfconverter
```

---

## Contributing

We welcome contributions! Here's how you can help:

- **Report bugs** - Open an issue with detailed reproduction steps
- **Suggest features** - Describe your use case and requirements
- **Submit mappings** - Share your YARRRML mappings as examples
- **Improve docs** - Help make the documentation clearer
- **Fix issues** - Submit pull requests with bug fixes or enhancements

### Adding Example Mappings

1. Create your `.yaml` mapping file
2. Test it thoroughly with `/api/test`
3. Add it to the `examples/` directory
4. Submit a pull request with:
   - The mapping file
   - A description of what it demonstrates
   - Sample data source (or URL to public data)

---

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

The authors would like to thank the Federal Government and the Heads of Government of the Länder for their funding and support within the framework of the [Platform Material Digital](https://www.materialdigital.de) consortium.

**Funded by:**
- [Federal Ministry of Education and Research (BMBF)](https://www.bmbf.de/bmbf/en/)
- [MaterialDigital](https://www.bmbf.de/SharedDocs/Publikationen/de/bmbf/5/31701_MaterialDigital.pdf?__blob=publicationFile&v=5) initiative
- Project [KupferDigital](https://www.materialdigital.de/project/1) (Project ID: 13XP5119)

---

## Support

- **Documentation:** You're reading it! 📖
- **API Docs:** http://localhost:6003/api/docs (when running)
- **Issues:** https://github.com/Mat-O-Lab/RDFConverter/issues
- **Organization:** https://github.com/Mat-O-Lab
- **Contact:** thomas.hanke@iwm.fraunhofer.de

---

**Made with ❤️ by the Mat-O-Lab team**
