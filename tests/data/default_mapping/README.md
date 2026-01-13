# Default Mapping for Testing

This directory is for storing a local copy of the default reference mapping for testing without network access.

## Reference Mapping

The official reference mapping URL is:
```
https://raw.githubusercontent.com/Mat-O-Lab/MapToMethod/refs/heads/main/examples/example-map.yaml
```

## Usage

### Option 1: Use Remote URL (Default)
Tests will automatically fetch the mapping from the URL above when no local file exists.

### Option 2: Use Local Copy (Offline Testing)
To test without network access:

1. Download the reference mapping:
   ```bash
   curl -o tests/data/default_mapping/example-map.yaml \
     https://raw.githubusercontent.com/Mat-O-Lab/MapToMethod/refs/heads/main/examples/example-map.yaml
   ```

2. Tests will automatically detect and use the local file

## How It Works

The test fixture in `conftest.py` checks for a local file first:
- If `tests/data/default_mapping/example-map.yaml` exists → uses local file
- Otherwise → fetches from remote URL

This allows for:
- ✅ Faster tests (no network delay)
- ✅ Offline testing
- ✅ Consistent test data
- ✅ Automatic fallback to remote URL

## Updating Local Copy

To update the local copy to the latest version:

```bash
# Download latest version
curl -o tests/data/default_mapping/example-map.yaml \
  https://raw.githubusercontent.com/Mat-O-Lab/MapToMethod/refs/heads/main/examples/example-map.yaml

# Verify it works
pytest tests/test_integration_mappings.py::test_default_mapping_from_ui -v
```

## Notes

- The local file is **optional** - tests work with or without it
- URL and namespace checks have been removed - tests are generic
- Template verification checks for any triples, not specific URLs
- This makes tests flexible for any mapping structure
