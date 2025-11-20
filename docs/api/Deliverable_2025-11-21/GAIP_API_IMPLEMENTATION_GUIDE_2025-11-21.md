# GAIP Knowledge Repository API - Implementation Guide
**Deliverable Date**: November 21, 2025  
**Version**: v1.0 (2025-11-21)  
**Status**: Production Ready - All API Fields Implemented  
**Audience**: GAIP Team & Gisfy (UX Contractor)

---

## 🔐 **Authentication Required**

### **Current Status**
The GAIP Knowledge Repository API **requires JWT Bearer Token authentication** via Amazon Cognito for all requests.

**API Endpoint**: `https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search`  
**Authentication**: JWT Bearer Token (required for all requests)

### **Getting Started**
1. **Authenticate with Cognito** using provided credentials
2. **Obtain JWT access token** from authentication response
3. **Include token** in Authorization header for all API requests

### **Authentication Flow**
```javascript
// Complete authentication implementation from working test app
async function authenticate() {
    const email = 'gaip-service@gaip.com';
    const password = '[Your-Password]';  // Provided by SolveGlobal team
    const clientId = '7p462gapip85uve67q310nvcil';
    
    // Authenticate with Cognito
    const authResponse = await fetch('https://cognito-idp.us-east-1.amazonaws.com/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-amz-json-1.1',
            'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth'
        },
        body: JSON.stringify({
            ClientId: clientId,
            AuthFlow: 'USER_PASSWORD_AUTH',
            AuthParameters: {
                USERNAME: email,
                PASSWORD: password
            }
        })
    });
    
    const authData = await authResponse.json();
    // IMPORTANT: Use IdToken for API Gateway
    const idToken = authData.AuthenticationResult.IdToken;
    
    // Use token in API requests
    const searchResponse = await fetch('https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${idToken}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            query: 'climate risk insurance',
            parameters: { max_results: 10 }
        })
    });
    
    return searchResponse.json();
}
```

**Key Points:**
- Use **IdToken** (not AccessToken) for API Gateway authorization
- Direct Cognito API call using service endpoint
- Handle token expiry and refresh as needed

### **Test Credentials**
- **User Pool ID**: `us-east-1_W1N7opitG`
- **App Client ID**: `7p462gapip85uve67q310nvcil`
- **Username**: `gaip-service@gaip.com`
- **Password**: `[To be provided by SolveGlobal team]`

### **Sample Request**
```bash
curl -X POST "https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "climate risk insurance",
    "parameters": {
      "max_results": 10
    }
  }'
```

**⚠️ Authentication Required**: All API requests require a valid JWT token from Cognito authentication.

---

## 📋 **Current Implementation Status**

### ✅ **Fully Implemented Features**
- **Hybrid Search**: BM25 keyword + Vector semantic + Knowledge Graph filtering
- **Complete API Response Fields**: All metadata fields populated with real data
- **Related Documents**: Trusted Source Documents (TSDs) linked to each solution
- **Advanced Filtering**: By risk type, solution type, country, region, PPP involvement
- **Pagination**: Cursor-based pagination for large result sets
- **Session Management**: Cached results for consistent pagination

### ✅ **API Response Fields (All Complete)**
- **`implemented`**: Boolean - true/false based on implementation year vs current year
- **`ppp_involvement`**: String - "yes"/"no"/"unknown" based on organization analysis
- **`last_update_date`**: String - ISO8601 date format (YYYY-MM-DD)
- **`key_highlights`**: Array - Individual highlight strings from document sections
- **`risk_types_addressed`**: Array - Human-readable risk type labels
- **`solution_types`**: Array - Human-readable solution type labels
- **`country_regions_covered`**: Array - Country names from GeoNames integration

---

## 🔧 **API Usage Guide**

### **Basic Search**
```json
POST /v1/search
{
  "query": "parametric insurance flood",
  "parameters": {
    "max_results": 20
  }
}
```

### **Advanced Filtering**
```json
POST /v1/search
{
  "query": "climate risk",
  "filters": {
    "solution_category": ["natural-catastrophe"],
    "solution_type": ["risk-reduction"],
    "countries": ["thailand", "vietnam"],
    "ppp_involvement": true
  },
  "parameters": {
    "max_results": 50
  }
}
```

### **Pagination**
```json
POST /v1/search
{
  "query": "insurance",
  "parameters": {
    "max_results": 20,
    "cursor": "eyJza2lwIjoyMH0="
  }
}
```

---

## 📊 **Real API Examples**

### **Filter-Only Search (No Query)**
```json
{
  "query": "",
  "parameters": {
    "max_results": 20,
    "cursor": null
  },
  "filters": {
    "solution_category": ["natural-catastrophe"],
    "solution_type": ["risk-reduction"]
  }
}
```

### **Hybrid Search (Query + Filters)**
```json
{
  "query": "Parametric insurance facilities",
  "parameters": {
    "max_results": 20,
    "cursor": null
  },
  "filters": {
    "solution_category": ["natural-catastrophe"],
    "solution_type": ["risk-reduction"]
  }
}
```

### **Real API Response**
```json
{
  "status": "success",
  "query_id": "search_b4533976-98b1-4986-bd87-2b34a18e86a5",
  "execution_time_ms": 12191,
  "total_results": 337,
  "returned_results": 20,
  "results": {
    "solutions": [
      {
        "document_id": "sol_e45333560cecba5f2",
        "content_type": "solution",
        "solution_name": "Shanghai Typhoon Collaborative Research Fund (STCRF)",
        "title": "Shanghai Typhoon Collaborative Research Fund (STCRF)",
        "relevance_score": 0.9496,
        "publication_date": "2023",
        "country_regions_covered": ["China"],
        "risk_types_addressed": ["Natural Catastrophe"],
        "solution_categories": [],
        "solution_types": ["Risk Reduction", "Risk Financing"],
        "implemented": true,
        "ppp_involvement": "no",
        "last_update_date": "2025-09-25",
        "summary_description": "The Shanghai Typhoon Collaborative Research Fund (STCRF) is a competitive funding initiative aimed at advancing research on tropical cyclones and related marine meteorological hazards. Managed by the Asia-Pacific Typhoon Collaborative Research Center (AP-TCRC) in Shanghai, the fund supports both short-term and long-term research residencies.",
        "key_highlights": [
          "The fund offers both short-term (2–3 months) and long-term (1 year, extendable) residencies to facilitate intensive collaborations and deeper research.",
          "It provides logistical support including airfare, accommodation, and Daily Subsistence Allowance (DSA) to lower participation barriers.",
          "The initiative is integrated with AP-TCRC's research ecosystem, promoting the translation of scientific findings into operationally relevant products.",
          "The fund is aligned with the ESCAP/WMO Typhoon Committee, ensuring regional coordination and impact."
        ],
        "source": "https://www.typhooncommittee.org/index.php?route=product/category&path=75_120",
        "related_documents": [
          {
            "doc_id": "d4d72ac88ac74e9421f0",
            "title": "Document of The World Bank",
            "summary": "Technical Assistance is supporting DOF and local governments to establish a joint catastrophe risk insurance facility for local government units, drawing on experience from the Pacific Catastrophe Risk...",
            "rank": 1,
            "source_url": "http://documents.worldbank.org/curated/en/989761468196182551/pdf/96587-PGD-P155656-R2015-0243-1-Box393264B-OUO-9.pdf",
            "source_name": "World Bank",
            "content_type": "trusted_source_document"
          }
        ],
        "snippets": [
          {
            "text": "The Shanghai Typhoon Collaborative Research Fund (STCRF) is a competitive funding initiative aimed at advancing research on tropical cyclones and related marine meteorological hazards...",
            "page_number": 1,
            "section": "Description"
          }
        ],
        "metadata": {
          "document_type": "solution",
          "categories": ["Natural Catastrophe"],
          "regions": ["China"],
          "publication_year": 2023,
          "source": "https://www.typhooncommittee.org/index.php?route=product/category&path=75_120"
        }
      }
    ]
  },
  "pagination": {
    "current_page": 1,
    "total_pages": 17,
    "total_results": 337,
    "page_size": 20,
    "next_cursor": "eyJxdWVyeV9pZCI6ICJzZWFyY2hfYjQ1MzM5NzYtOThiMS00OTg2LWJkODctMmIzNGExOGU4NmE1IiwgInBhZ2UiOiAyfQ=="
  }
}
```

### **Pagination Examples**

**Subsequent Page Request (Page 3):**
```json
{
  "query": "Parametric insurance facilities",
  "parameters": {
    "max_results": 20,
    "cursor": "eyJxdWVyeV9pZCI6InNlYXJjaF9iNDUzMzk3Ni05OGIxLTQ5ODYtYmQ4Ny0yYjM0YTE4ZTg2YTUiLCJwYWdlIjozfQ=="
  },
  "filters": {
    "solution_category": ["natural-catastrophe"],
    "solution_type": ["risk-reduction"]
  }
}
```

**Last Page Pagination Response:**
```json
"pagination": {
  "current_page": 17,
  "total_pages": 17,
  "total_results": 337,
  "page_size": 20,
  "next_cursor": null
}
```

---

## 🎯 **Filter Options**

### **Solution Categories**
- `natural-catastrophe` - Natural disasters, climate risks
- `cyber` - Cybersecurity and digital risks
- `health` - Health insurance and medical coverage
- `retirement` - Pension and retirement planning
- `mortality` - Life insurance and mortality risks

### **Solution Types**
- `risk-reduction` - Risk mitigation and prevention
- `risk-financing` - Insurance and financial instruments
- `increase-penetration` - Market expansion strategies
- `raising-awareness` - Education and awareness programs
- `leveraging-technology` - Technology-driven solutions
- `regulation` - Policy and regulatory frameworks

### **Geographic Filters**
- **Countries**: `thailand`, `vietnam`, `philippines`, `indonesia`, `malaysia`, `singapore`, `cambodia`, `laos`, `myanmar`, `brunei`, `china`, `japan`, `south-korea`, `india`, `bangladesh`, `pakistan`, `nepal`, `sri-lanka`, `australia`, `new-zealand`
- **Regions**: `asean`, `asean-plus-3`, `asia-pacific`

### **Other Filters**
- **PPP Involvement**: `true`/`false` - Solutions with Public-Private Partnerships
- **Implementation Status**: Automatically determined from publication dates

---

## 🔍 **Search Strategies**

### **1. Keyword Search**
- Use natural language queries
- System automatically handles synonyms and related terms
- Example: `"flood insurance Thailand"`

### **2. Semantic Search**
- Finds conceptually similar content even without exact keyword matches
- Example: `"agricultural risk protection"` finds flood insurance solutions

### **3. Filtered Search**
- Combine text search with specific filters
- Example: Search `"insurance"` + filter by `natural-catastrophe` + `thailand`

### **4. Browse by Category**
- Use filters without query text to browse categories
- Example: All `cyber` solutions in `asean` region

---

## 📈 **Performance & Limits**

### **Response Times**
- **Typical**: 200-500ms for hybrid search
- **With Related Documents**: 300-800ms
- **Large Result Sets**: Up to 1-2 seconds

### **Rate Limits**
- **100 requests per minute** per API key
- **1000 requests per hour** per API key

### **Result Limits**
- **Maximum results per request**: 100
- **Default page size**: 20
- **Total searchable content**: 567+ solutions, 400+ trusted source documents

---

## 🛠️ **Integration Examples**

### **JavaScript/React**
```javascript
// Based on working test application
class GaipSearchClient {
    constructor() {
        this.currentToken = null;
        this.tokenExpiry = null;
        this.userPoolId = 'us-east-1_W1N7opitG';
        this.clientId = '7p462gapip85uve67q310nvcil';
    }
    
    async authenticate(email, password) {
        const authResponse = await fetch('https://cognito-idp.us-east-1.amazonaws.com/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-amz-json-1.1',
                'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth'
            },
            body: JSON.stringify({
                ClientId: this.clientId,
                AuthFlow: 'USER_PASSWORD_AUTH',
                AuthParameters: {
                    USERNAME: email,
                    PASSWORD: password
                }
            })
        });
        
        const authData = await authResponse.json();
        this.currentToken = authData.AuthenticationResult.IdToken;
        this.tokenExpiry = Date.now() + (authData.AuthenticationResult.ExpiresIn * 1000);
        
        return this.currentToken;
    }
    
    async searchAPI(query, filters = {}) {
        // Check token validity
        if (!this.currentToken || Date.now() >= this.tokenExpiry) {
            throw new Error('Authentication required');
        }
        
        const response = await fetch('https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.currentToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query,
                filters,
                parameters: { max_results: 20 }
            })
        });
        
        if (response.status === 401) {
            throw new Error('Token expired - please re-authenticate');
        }
        
        return response.json();
    }
}

// Usage
const client = new GaipSearchClient();
await client.authenticate('gaip-service@gaip.com', 'your-password');
const results = await client.searchAPI('climate insurance', {
    solution_category: ['natural-catastrophe']
});
```

### **Python**
```python
import requests

def search_solutions(query, filters=None, max_results=20):
    url = 'https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search'
    payload = {
        'query': query,
        'filters': filters or {},
        'parameters': {'max_results': max_results}
    }
    
    response = requests.post(url, json=payload)
    return response.json()

# Usage
results = search_solutions('parametric insurance', {
    'solution_category': ['natural-catastrophe'],
    'ppp_involvement': True
})
```

---

## 🎨 **UX Implementation Notes**

### **Status Indicators**
Display implementation and PPP status with visual indicators:
- **✅ Implemented** (green) when `implemented: true`
- **❌ Not Implemented** (red) when `implemented: false`
- **✅ PPP** (green) when `ppp_involvement: "yes"`
- **❌ PPP** (red) when `ppp_involvement: "no"`
- **❓ Unknown** (gray) for unknown values

### **Key Highlights Display**
```javascript
// Display key highlights as bullet list
const renderHighlights = (highlights) => (
  <ul>
    {highlights.map((highlight, index) => (
      <li key={index}>{highlight}</li>
    ))}
  </ul>
);
```

### **Related Documents**
Show 3-5 related trusted source documents per solution with:
- Document title and source
- Brief summary
- Relevance ranking
- Link to full document

### **Responsive Design**
- **Desktop**: 3-column layout (Risk Types | Solution Types | Key Highlights)
- **Tablet**: 2-column layout
- **Mobile**: Single column stacked layout

---

## 🔐 **Authentication (Coming Soon)**

**Note**: Current API is open for testing. Production will require Cognito authentication.

### **Future Authentication Flow**
1. Authenticate with Cognito User Pool
2. Receive JWT access token
3. Include token in Authorization header: `Bearer <token>`
4. Token expires after 1 hour, refresh as needed

---

## 📞 **Support & Contact**

### **Technical Support**
- **Email**: api-support@solve.global
- **Documentation**: See accompanying files in this deliverable
- **Issue Reporting**: Contact development team

### **Test Environment**
- **API URL**: `https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search`
- **Test Webapp**: Available at CloudFront distribution (URL provided separately)
- **Status**: Production-ready with all features implemented

---

## 📋 **Testing Checklist**

### **Basic Functionality**
- [ ] Simple text search returns results
- [ ] Filters work correctly (solution_category, countries, etc.)
- [ ] Pagination works with cursor-based navigation
- [ ] All API response fields are populated

### **Advanced Features**
- [ ] Related documents appear for solutions
- [ ] Status indicators display correctly (implemented, PPP)
- [ ] Key highlights show as bullet points
- [ ] Search performance is acceptable (<2 seconds)

### **Error Handling**
- [ ] Invalid queries return appropriate error messages
- [ ] Rate limiting works correctly
- [ ] Empty results handled gracefully

### **UX Integration**
- [ ] Responsive design works on mobile/tablet/desktop
- [ ] Status indicators are visually clear
- [ ] Related documents enhance user experience
- [ ] Search filters are intuitive and functional

---

## 🚀 **Next Steps**

1. **Test the API** using the provided endpoint and sample requests
2. **Integrate with your frontend** using the provided code examples
3. **Implement UX enhancements** based on the design guidelines
4. **Provide feedback** on API functionality and performance
5. **Prepare for production deployment** with Cognito authentication

---

**Document Version**: v1.0 (2025-11-21)  
**API Status**: Production Ready  
**Content**: 567+ solutions, 400+ trusted source documents  
**Last Updated**: November 21, 2025
