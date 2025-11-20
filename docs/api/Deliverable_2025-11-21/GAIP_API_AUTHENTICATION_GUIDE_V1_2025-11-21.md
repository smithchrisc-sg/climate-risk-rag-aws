# GAIP API Authentication Guide - v1.0 (2025-11-21)

**Last Updated**: November 21, 2025  
**Status**: Current Implementation - Open API for Testing  
**Future**: Cognito JWT Authentication for Production

---

## 🚨 **Current Status (November 2025)**

### **Testing Phase - No Authentication Required**
The GAIP Knowledge Repository API is currently **open for testing** without authentication requirements.

**Current API Endpoint**: `https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search`

**Usage**: Direct API calls without authentication headers
```bash
curl -X POST "https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "climate risk insurance"}'
```

### **Production Deployment - Cognito Authentication**
When deployed to production, the API will require JWT Bearer Token authentication via Amazon Cognito.

---

## 🔐 **Future Authentication Implementation**

### **Overview**
The production GAIP Knowledge Repository API will use **JWT Bearer Token authentication** via Amazon Cognito. All authenticated endpoints will require a valid JWT token in the Authorization header.

### **Authentication Flow**
1. **User Registration/Login** - Authenticate with Cognito User Pool
2. **Receive JWT Token** - Cognito issues access token and ID token
3. **API Requests** - Include Bearer token in Authorization header
4. **Token Validation** - API Gateway validates token via Lambda authorizer
5. **Token Refresh** - Use refresh token to obtain new access tokens

---

## 🚀 **Getting Started (Production)**

### **Prerequisites**
You will receive from GAIP:
- **Cognito User Pool ID**: `us-east-1_W1N7opitG`
- **App Client ID**: `7p462gapip85uve67q310nvcil`
- **Cognito Domain**: `gaip-auth.auth.us-east-1.amazoncognito.com` (when configured)
- **API Base URL**: `https://api.solve.global/gaip/v1` (production)

### **Test Credentials**
For testing and development:
- **Username**: `gaip-service@gaip.com`
- **Password**: `[To be provided by SolveGlobal team]`
- **User Pool**: `us-east-1_W1N7opitG`

### **User Registration**
New users must be registered in the GAIP Cognito User Pool. Contact your GAIP administrator for:
- User account creation
- Organization assignment (GAIP, Gisfy, etc.)
- Role/permission configuration

---

## 🔧 **Authentication Methods**

### **Method 1: Hosted UI (Recommended for Web Applications)**

Amazon Cognito provides a hosted authentication UI for user login.

**Login URL Format:**
```
https://gaip-auth.auth.us-east-1.amazoncognito.com/login?
  client_id=7p462gapip85uve67q310nvcil&
  response_type=code&
  scope=openid+email+profile&
  redirect_uri=<your-callback-url>
```

**Flow:**
1. Redirect user to Cognito hosted UI
2. User authenticates with username/password
3. Cognito redirects to your callback URL with authorization code
4. Exchange authorization code for JWT tokens

**Token Exchange:**
```bash
curl -X POST https://gaip-auth.auth.us-east-1.amazoncognito.com/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&\
      client_id=7p462gapip85uve67q310nvcil&\
      code=<authorization-code>&\
      redirect_uri=<your-callback-url>"
```

**Response:**
```json
{
  "access_token": "eyJraWQiOiJ...",
  "id_token": "eyJraWQiOiJ...",
  "refresh_token": "eyJjdHkiOiJ...",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

### **Method 2: Direct Authentication (Server-to-Server)**

For backend services and automation, use the AWS SDK or Cognito API directly.

**Using AWS SDK (Python example):**
```python
import boto3

client = boto3.client('cognito-idp', region_name='us-east-1')

response = client.initiate_auth(
    ClientId='7p462gapip85uve67q310nvcil',
    AuthFlow='USER_PASSWORD_AUTH',
    AuthParameters={
        'USERNAME': 'gaip-service@gaip.com',
        'PASSWORD': '[To be provided by SolveGlobal team]'
    }
)

access_token = response['AuthenticationResult']['AccessToken']
id_token = response['AuthenticationResult']['IdToken']
```

### **Method 3: Client Credentials (Machine-to-Machine)**

For service accounts without user interaction.

```bash
curl -X POST https://gaip-auth.auth.us-east-1.amazoncognito.com/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&\
      client_id=7p462gapip85uve67q310nvcil&\
      client_secret=<app-client-secret>&\
      scope=<custom-scope>"
```

---

## 🔑 **Using JWT Tokens**

### **Making Authenticated API Requests**

Include the access token in the Authorization header:

```bash
curl -X POST https://api.solve.global/gaip/v1/search \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "parametric insurance flood risk",
    "filters": {
      "solution_category": ["natural_catastrophe"],
      "risk_type": ["flood"]
    }
  }'
```

### **Token Structure**

Cognito JWT tokens contain:
- **sub**: Unique user identifier (UUID)
- **cognito:username**: Username
- **cognito:groups**: User groups/roles
- **email**: User email address
- **exp**: Expiration timestamp
- **iat**: Issued at timestamp

### **Token Expiration**

- **Access Token**: 1 hour (configurable)
- **ID Token**: 1 hour (configurable)
- **Refresh Token**: 30 days (configurable)

---

## 🔄 **Token Refresh**

When access tokens expire, use the refresh token to obtain new tokens without re-authentication.

```bash
curl -X POST https://gaip-auth.auth.us-east-1.amazoncognito.com/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token&\
      client_id=7p462gapip85uve67q310nvcil&\
      refresh_token=<refresh-token>"
```

**Response:**
```json
{
  "access_token": "eyJraWQiOiJ...",
  "id_token": "eyJraWQiOiJ...",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

---

## 📋 **Endpoint Authentication Requirements**

| Endpoint | Method | Current Status | Production Status |
|----------|--------|----------------|-------------------|
| `/search` | POST | ❌ No Auth Required | ✅ JWT Bearer Token |
| `/repository/last-update` | GET | ❌ No Auth Required | ❌ Public |
| `/repository/solution-count` | GET | ❌ No Auth Required | ❌ Public |

---

## ⚠️ **Error Responses**

### **401 Unauthorized**

**Token Missing:**
```json
{
  "message": "Unauthorized"
}
```

**Token Expired:**
```json
{
  "message": "Token expired"
}
```

**Invalid Token:**
```json
{
  "message": "Invalid token"
}
```

### **403 Forbidden**

**Insufficient Permissions:**
```json
{
  "message": "Forbidden - Insufficient permissions"
}
```

---

## 🔒 **Security Best Practices**

### **Token Storage**

- **Web Applications**: Store tokens in memory or secure HTTP-only cookies
- **Mobile Apps**: Use secure storage (iOS Keychain, Android Keystore)
- **Never**: Store tokens in localStorage or client-side code repositories

### **Token Transmission**

- **Always use HTTPS** for API requests
- **Never log tokens** in application logs
- **Never include tokens** in URLs or query parameters

### **Token Lifecycle**

- **Implement token refresh** before expiration
- **Clear tokens on logout** from client storage
- **Handle 401 errors** by refreshing or re-authenticating

---

## 💻 **Integration Examples**

### **JavaScript/TypeScript (Web)**

```javascript
// Current implementation (no auth)
async function searchAPI(query, filters) {
  const response = await fetch('https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ query, filters })
  });
  
  return response.json();
}

// Future implementation (with auth)
async function searchAPIWithAuth(query, filters) {
  const accessToken = getStoredAccessToken(); // Your token storage method
  
  const response = await fetch('https://api.solve.global/gaip/v1/search', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ query, filters })
  });
  
  if (response.status === 401) {
    // Token expired - refresh and retry
    await refreshToken();
    return searchAPIWithAuth(query, filters);
  }
  
  return response.json();
}
```

### **Python**

```python
import requests

# Current implementation (no auth)
def search_api_current(query, filters):
    url = 'https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search'
    payload = {
        'query': query,
        'filters': filters
    }
    
    response = requests.post(url, json=payload)
    return response.json()

# Future implementation (with auth)
def search_api_with_auth(query, filters, access_token):
    url = 'https://api.solve.global/gaip/v1/search'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    payload = {
        'query': query,
        'filters': filters
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 401:
        # Token expired - refresh and retry
        access_token = refresh_cognito_token()
        return search_api_with_auth(query, filters, access_token)
    
    return response.json()
```

### **cURL**

```bash
# Current implementation (no auth)
curl -X POST https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "climate risk insurance",
    "filters": {
      "solution_category": ["natural_catastrophe"]
    }
  }'

# Future implementation (with auth)
ACCESS_TOKEN="eyJraWQiOiJ..."

curl -X POST https://api.solve.global/gaip/v1/search \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "climate risk insurance",
    "filters": {
      "solution_category": ["natural_catastrophe"]
    }
  }'
```

---

## 🛠️ **Troubleshooting**

### **Common Issues**

**Problem**: "Unauthorized" error despite having token  
**Solution**: Verify token is included with "Bearer " prefix in Authorization header

**Problem**: Token works initially but fails after time  
**Solution**: Implement token refresh logic before expiration

**Problem**: "Invalid token" error  
**Solution**: Ensure you're using the access_token, not id_token or refresh_token

**Problem**: CORS errors in browser  
**Solution**: Ensure your domain is whitelisted in Cognito App Client settings

### **Token Validation**

To inspect token contents (for debugging only):
1. Visit [jwt.io](https://jwt.io)
2. Paste your token
3. View decoded payload (do not paste tokens on public sites in production)

---

## 📞 **Support**

For authentication issues or access requests:
- **Email**: api-support@solve.global
- **Documentation**: See `GAIP_API_DOCUMENTATION_V1_2025-11-21.md` for API details
- **Current Testing**: Use open API endpoint without authentication

---

## 📋 **OAuth 2.0 Scopes**

GAIP API will use the following scopes:

| Scope | Description |
|-------|-------------|
| `openid` | Required for OpenID Connect |
| `email` | Access to user email |
| `profile` | Access to user profile information |
| `gaip/search` | Permission to use search endpoint |

Custom scopes may be assigned based on organization and role.

---

## 🚀 **Migration Timeline**

### **Phase 1: Current (November 2025)**
- ✅ Open API for testing and development
- ✅ No authentication required
- ✅ Full API functionality available

### **Phase 2: Production Deployment**
- 🔄 Cognito User Pool setup
- 🔄 JWT authentication implementation
- 🔄 User account provisioning
- 🔄 Production API endpoint activation

### **Phase 3: Go-Live**
- 🔄 Authentication required for all requests
- 🔄 User training and onboarding
- 🔄 Support and monitoring

---

**Document Version**: v1.0 (2025-11-21)  
**Authentication Method**: Future - Amazon Cognito with OAuth 2.0 / OpenID Connect  
**Token Type**: JWT Bearer Tokens  
**Current Status**: Open API for Testing
