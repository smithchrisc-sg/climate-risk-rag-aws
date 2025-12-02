# GAIP API Authentication Guide - v1.0 (2025-11-21)

**Last Updated**: November 21, 2025  
**Status**: JWT Authentication Required  
**Implementation**: Cognito User Pool Authentication

---

## 🔐 **Authentication Required**

### **JWT Bearer Token Authentication**
The GAIP Knowledge Repository API **requires JWT Bearer Token authentication** via Amazon Cognito for all requests.

**Current API Endpoint**: `https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search`

**Usage**: All API calls require Authorization header with JWT token
```bash
curl -X POST "https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "climate risk insurance"}'
```

### **Authentication is Mandatory**
- ✅ **JWT authentication implemented** and active
- ✅ **Cognito User Pool configured** with service accounts
- ✅ **API Gateway authorizer** validates all requests
- ❌ **No requests allowed** without valid JWT token

---

## 🔐 **Current Authentication Implementation**

### **Overview**
The GAIP Knowledge Repository API uses **JWT Bearer Token authentication** via Amazon Cognito. All API endpoints require a valid JWT token in the Authorization header.

### **Authentication Flow**
1. **User Login** - Authenticate with Cognito User Pool using username/password
2. **Receive JWT Token** - Cognito returns access token, ID token, and refresh token
3. **API Requests** - Include access token in Authorization header
4. **Token Validation** - API Gateway validates token via Lambda authorizer
5. **Token Refresh** - Use refresh token to obtain new access tokens when expired

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
- Organization assignment
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

| Endpoint | Method | Authentication Status |
|----------|--------|----------------------|
| `/search` | POST | ✅ JWT Bearer Token Required |
| `/repository/last-update` | GET | ✅ JWT Bearer Token Required |
| `/repository/solution-count` | GET | ✅ JWT Bearer Token Required |

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

## 💻 **Complete JavaScript Authentication Example**

### **Frontend Authentication Implementation**
Based on the working test application, here's the complete authentication flow:

```javascript
// Global variables for token management
let currentToken = null;
let tokenExpiry = null;

async function authenticate() {
    const email = 'gaip-service@gaip.com';  // Your provided username
    const password = '[Your-Password]';     // Password set by SolveGlobal team
    const userPoolId = 'us-east-1_W1N7opitG';
    const clientId = '7p462gapip85uve67q310nvcil';
    const clientSecret = '[Your-Client-Secret]';  // If app client has secret
    
    try {
        // Calculate SECRET_HASH using Web Crypto API (if client secret is configured)
        const message = email + clientId;
        const key = await window.crypto.subtle.importKey(
            'raw',
            new TextEncoder().encode(clientSecret),
            { name: 'HMAC', hash: 'SHA-256' },
            false,
            ['sign']
        );
        const signature = await window.crypto.subtle.sign('HMAC', key, new TextEncoder().encode(message));
        const secretHash = btoa(String.fromCharCode(...new Uint8Array(signature)));
        
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
                    PASSWORD: password,
                    SECRET_HASH: secretHash  // Include if client secret is configured
                }
            })
        });
        
        if (!authResponse.ok) {
            const errorData = await authResponse.json();
            throw new Error(errorData.message || `Authentication failed: ${authResponse.status}`);
        }
        
        const authData = await authResponse.json();
        
        // IMPORTANT: Use IdToken for API Gateway Cognito User Pool authorizer
        currentToken = authData.AuthenticationResult.IdToken;
        tokenExpiry = Date.now() + (authData.AuthenticationResult.ExpiresIn * 1000);
        
        console.log('Authentication successful!');
        return currentToken;
        
    } catch (error) {
        console.error('Authentication error:', error);
        throw error;
    }
}

// Use token in API requests
async function searchWithAuth(query, filters = {}) {
    // Check if token exists and is not expired
    if (!currentToken || Date.now() >= tokenExpiry) {
        await authenticate();
    }
    
    const response = await fetch('https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${currentToken}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            query: query,
            filters: filters,
            parameters: { max_results: 20 }
        })
    });
    
    if (response.status === 401) {
        // Token expired, re-authenticate
        await authenticate();
        return searchWithAuth(query, filters);
    }
    
    return response.json();
}
```

### **Key Implementation Notes**

1. **Use IdToken**: The API Gateway Cognito User Pool authorizer expects the `IdToken`, not the `AccessToken`
2. **SECRET_HASH**: Required if your app client is configured with a client secret
3. **Token Management**: Store token and expiry time, refresh when needed
4. **Error Handling**: Handle 401 responses by re-authenticating
5. **Direct Cognito API**: Uses Cognito service endpoint directly, not AWS SDK

### **Simplified Version (No Client Secret)**
If the app client doesn't have a client secret configured:

```javascript
async function authenticateSimple() {
    const authResponse = await fetch('https://cognito-idp.us-east-1.amazonaws.com/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-amz-json-1.1',
            'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth'
        },
        body: JSON.stringify({
            ClientId: '7p462gapip85uve67q310nvcil',
            AuthFlow: 'USER_PASSWORD_AUTH',
            AuthParameters: {
                USERNAME: 'gaip-service@gaip.com',
                PASSWORD: '[Your-Password]'
                // No SECRET_HASH needed if no client secret
            }
        })
    });
    
    const authData = await authResponse.json();
    return authData.AuthenticationResult.IdToken;
}
```

### **JavaScript/TypeScript (Web)**

```javascript
// Current implementation (with required auth)
async function searchAPI(query, filters) {
  const accessToken = await getAccessToken(); // Get token from Cognito
  
  const response = await fetch('https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search', {
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
    return searchAPI(query, filters);
  }
  
  return response.json();
}

// Cognito authentication function
async function getAccessToken() {
  // Implementation depends on your Cognito setup
  // See full example in app.js integration section
}
```

### **Python**

```python
import requests

def search_api(query, filters, access_token):
    url = 'https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search'
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
        return search_api(query, filters, access_token)
    
    return response.json()

def get_cognito_token(username, password):
    import boto3
    client = boto3.client('cognito-idp', region_name='us-east-1')
    
    response = client.initiate_auth(
        ClientId='7p462gapip85uve67q310nvcil',
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': username,
            'PASSWORD': password
        }
    )
    
    return response['AuthenticationResult']['AccessToken']
```

### **cURL**

```bash
# Get JWT token first (using AWS CLI)
ACCESS_TOKEN=$(aws cognito-idp initiate-auth \
  --client-id 7p462gapip85uve67q310nvcil \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=gaip-service@gaip.com,PASSWORD=YourPassword \
  --region us-east-1 \
  --query 'AuthenticationResult.AccessToken' \
  --output text)

# Use token in API request
curl -X POST https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search \
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
- **Documentation**: See `GAIP_API_DOCUMENTATION_V1_2025-11-21.md` for API details
- **Production**: JWT authentication required for all requests

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

**Document Version**: v1.0 (2025-11-21)  
**Authentication Method**: Future - Amazon Cognito with OAuth 2.0 / OpenID Connect  
**Token Type**: JWT Bearer Tokens  
**Current Status**: JWT Authentication Required
