# GAIP API Quick Reference v2.0 - Solution-Focused

## 🔍 **Endpoints**
```
POST /search                    # Search solutions and documents
GET /repository/last-update     # Get last repository update
GET /repository/solution-count  # Get solution count
```

## 📤 **Request Format**
```json
{
  "query": "parametric insurance flood risk",
  "filters": {
    "solution_category": ["risk reduction", "insurance penetration"],
    "risk_type": ["flood", "agricultural"],
    "geographic_scope": ["ASEAN", "country"],
    "ppp_involvement": true
  },
  "parameters": {
    "max_results": 20
  }
}
```

## 🆕 **New Filter Parameters**
| Filter | Type | Options |
|--------|------|---------|
| `solution_category` | array | `["risk reduction", "insurance penetration", "risk financing"]` |
| `solution_type` | array | Solution subcategories (open list) |
| `risk_type` | array | `["food", "cyber", "drought", "health", "flood", ...]` |
| `geographic_scope` | array | `["Asia", "ASEAN+3", "ASEAN", "country", "province/state", "city/muni"]` |
| `ppp_involvement` | boolean | Public-Private Partnership involvement |

## 📥 **New Response Fields**
| Field | Type | Description |
|-------|------|-------------|
| `solution_name` | string | Name of the solution |
| `publication_date` | string | Publication date (YYYY-MM-DD) |
| `country_regions_covered` | array | Countries/regions covered |
| `risk_types_addressed` | array | Risk types (ontology-matched) |
| `solution_categories` | array | Solution categories |
| `solution_types` | array | Solution subcategories |
| `implemented` | enum | `"yes"`, `"no"`, `"unknown"` |
| `ppp_involvement` | enum | `"yes"`, `"no"`, `"unknown"` |
| `summary_description` | string | Solution summary paragraph |
| `key_highlights` | array | Bullet point highlights |
| `results_outcomes` | string | Results and outcomes |
| `source_links` | array | Links to sources |
| `source` | string | Source organization |

## 🔗 **Repository Metadata**
```bash
# Last update
GET /repository/last-update
# Returns: {"last_update": "2024-09-24T08:00:00Z", ...}

# Solution count  
GET /repository/solution-count
# Returns: {"total_solutions": 1247, "breakdown": {...}}
```

## 💡 **Example Queries**
```json
// Find drought insurance solutions
{
  "query": "drought insurance smallholder farmers",
  "filters": {
    "risk_type": ["drought", "agricultural"],
    "solution_category": ["risk reduction"]
  }
}

// Find implemented PPP solutions in ASEAN
{
  "query": "public private partnership insurance",
  "filters": {
    "geographic_scope": ["ASEAN"],
    "ppp_involvement": true,
    "implemented": "yes"
  }
}
```
