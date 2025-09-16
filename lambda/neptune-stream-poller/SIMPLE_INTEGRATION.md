# Simple Ontology Filter Integration

## 🎯 **No Stubs, No Complexity - Just Add Filtering**

### **Step 1: Modify Handler File**

Edit `neptune_to_es/neptune_sparql_es_handler.py`:

**Add import at top:**
```python
from ontology_filter import get_ontology_filter
```

**Modify `filter_records` method (around line 191):**
```python
def filter_records(self, records, client):
    """
    Filters records to be stored in Elastic Search.
    Enhanced with ontology filtering for cost optimization.
    """
    
    # ONTOLOGY FILTERING - Add this block at the beginning
    ontology_filter = get_ontology_filter()
    if ontology_filter.filtering_enabled:
        original_count = len(records)
        records = ontology_filter.filter_records(records)
        logger.info(f"Ontology filter: {original_count} → {len(records)} records")
        
        # If no records remain, return early
        if not records:
            logger.info("No records remaining after ontology filtering")
            return []
    
    # EXISTING CODE CONTINUES UNCHANGED...
    excluded_types = get_excluded_datatypes("sparql")
    excluded_properties = get_excluded_properties()
    
    # ... rest of method unchanged
```

### **Step 2: Also Modify String Handler (if needed)**

Edit `neptune_to_es/neptune_sparql_es_string_indexing_handler.py`:

**Same changes as above** - add import and filtering block.

### **Step 3: Deploy**

```bash
cd /Users/chris/climate-risk-rag-aws/lambda/neptune-stream-poller
./deploy.sh
```

### **Step 4: Enable Filtering**

```bash
aws lambda update-function-configuration \
    --function-name "NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3" \
    --environment Variables='{
        "ONTOLOGY_FILTERING_ENABLED": "true",
        "ONTOLOGY_GRAPHS": "http://climate-risk-ontology,http://geonames-ontology"
    }'
```

### **Step 5: Monitor**

```bash
aws logs tail /aws/lambda/NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3 --follow
```

Look for log messages:
- `"Ontology filter: 1000 → 150 records"`
- `"Filtered 1000 records → 150 ontology records (85.0% filtered out)"`

## 🎯 **That's It!**

- **No stubs** - work with actual record format
- **No complexity** - just add filtering at the start
- **Test in production** - with real Neptune stream data
- **Easy rollback** - disable via environment variable

The ontology filter is already updated to handle the Neptune record format correctly.

---

**Total changes: 3 lines of code + environment variable**
