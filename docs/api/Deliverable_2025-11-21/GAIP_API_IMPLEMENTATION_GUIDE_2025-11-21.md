# GAIP Knowledge Repository API - Implementation Guide
**Deliverable Date**: November 21, 2025  
**Version**: v1.0 (2025-11-21)  
**Status**: Production Ready - All API Fields Implemented

---

## 🔐 **Authentication**

The GAIP Knowledge Repository API requires JWT Bearer Token authentication via Amazon Cognito for all requests.

**API Endpoint**: `https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search`  
**Authentication**: JWT Bearer Token (required for all requests)

### **Authentication Implementation**
Here's a simple JavaScript example that illustrates the mechanism.

```javascript
async function authenticate() {
    const email = 'gaip-service@gaip.com';
    const password = '[Your-Password]';  // Provided by SolveGlobal team
    const clientId = '7p462gapip85uve67q310nvcil';
    
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

**Authentication Details:**
- **User Pool ID**: `us-east-1_W1N7opitG`
- **App Client ID**: `7p462gapip85uve67q310nvcil`
- **Username**: `gaip-service@gaip.com`
- **Password**: `[To be provided by SolveGlobal team]`
- **Token Type**: Use IdToken (not AccessToken) for API Gateway authorization

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

---

## 📋 **API Features**

### **Implemented Capabilities**
- **Complete API Response Fields**: All metadata fields populated with real data
- **Related Documents**: Trusted Source Documents (TSDs) linked to each solution
- **Advanced Filtering**: By risk type, solution type, country, region, PPP involvement
- **Pagination**: Cursor-based pagination for large result sets
- **Session Management**: Cached results for consistent pagination

### **API Response Fields**
- **`implemented`**: Boolean - true/false based on implementation year vs current year
- **`ppp_involvement`**: String - "yes"/"no"/"unknown" based on organization analysis
- **`last_update_date`**: String - ISO8601 date format (YYYY-MM-DD)
- **`key_highlights`**: Array - Individual highlight strings from document sections
- **`risk_types_addressed`**: Array - Human-readable risk type labels
- **`solution_types`**: Array - Human-readable solution type labels
- **`country_regions_covered`**: Array - Country names from GeoNames integration

---

## 🔧 **API Usage**

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
    "cursor": "eyJxdWVyeV9pZCI6InNlYXJjaF9iNDUzMzk3Ni05OGIxLTQ5ODYtYmQ4Ny0yYjM0YTE4ZTg2YTUiLCJwYWdlIjozfQ=="
  }
}
```

### **Sample API Response**
```json
{
  "status": "success",
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
        "summary_description": "The Shanghai Typhoon Collaborative Research Fund (STCRF) is a competitive funding initiative aimed at advancing research on tropical cyclones and related marine meteorological hazards.",
        "key_highlights": [
          "The fund offers both short-term (2–3 months) and long-term (1 year, extendable) residencies to facilitate intensive collaborations and deeper research.",
          "It provides logistical support including airfare, accommodation, and Daily Subsistence Allowance (DSA) to lower participation barriers."
        ],
        "source": "https://www.typhooncommittee.org/index.php?route=product/category&path=75_120",
        "related_documents": [
          {
            "doc_id": "d4d72ac88ac74e9421f0",
            "title": "Document of The World Bank",
            "summary": "Technical Assistance is supporting DOF and local governments to establish a joint catastrophe risk insurance facility for local government units...",
            "rank": 1,
            "source_url": "http://documents.worldbank.org/curated/en/989761468196182551/pdf/96587-PGD-P155656-R2015-0243-1-Box393264B-OUO-9.pdf",
            "source_name": "World Bank",
            "content_type": "trusted_source_document"
          }
        ],
        "metadata": {
          "document_type": "solution",
          "categories": ["Natural Catastrophe"],
          "regions": ["China"],
          "publication_year": 2023
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

---

## 🎯 **Available Filters**

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

---

## 📈 **Performance & Limits**

Note that this is not a production system, so response times can be slower. We will endeavor to keep the backend systems up and running for testing availability. For best performance, keep page size ≤ 10.

The knowledge repository is not yet fully populated. There are approximately 550 solutions in the system and a small number of related trusted source documents. Not all solution results will have related trusted source documents. Because the system is not fully populated, you should not considered relevance when looking at related documents - consider that they are there to facilitate API testing. Moreover, note that related trusted source documents are not returned for filter-only searches - a search string is required to see that functionality.


---

## 🛠️ **Integration Examples**

### **JavaScript/React**
```javascript
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
```

### **Python**
```python
import requests
import json

class GaipSearchClient:
    def __init__(self):
        self.current_token = None
        self.client_id = '7p462gapip85uve67q310nvcil'
        self.api_url = 'https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search'
    
    def authenticate(self, email, password):
        auth_url = 'https://cognito-idp.us-east-1.amazonaws.com/'
        headers = {
            'Content-Type': 'application/x-amz-json-1.1',
            'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth'
        }
        payload = {
            'ClientId': self.client_id,
            'AuthFlow': 'USER_PASSWORD_AUTH',
            'AuthParameters': {
                'USERNAME': email,
                'PASSWORD': password
            }
        }
        
        response = requests.post(auth_url, headers=headers, json=payload)
        auth_data = response.json()
        self.current_token = auth_data['AuthenticationResult']['IdToken']
        return self.current_token
    
    def search(self, query, filters=None, max_results=20):
        if not self.current_token:
            raise Exception('Authentication required')
        
        headers = {
            'Authorization': f'Bearer {self.current_token}',
            'Content-Type': 'application/json'
        }
        payload = {
            'query': query,
            'filters': filters or {},
            'parameters': {'max_results': max_results}
        }
        
        response = requests.post(self.api_url, headers=headers, json=payload)
        return response.json()
```


---

**Document Version**: v1.0 (2025-11-21)  
**API Status**: Production Ready  
**Last Updated**: November 21, 2025
