# GAIP API Authentication & Testing Guide
**Version**: 2.0  
**Date**: September 24, 2025  
**Purpose**: Complete guide for API authentication, token generation, and test webapp usage

---

## 🔐 **Authentication Overview**

The GAIP Knowledge Repository API uses **JWT Bearer Token authentication** implemented via a custom Lambda authorizer (`gaip-jwt-authorizer`).

### **Authentication Flow**
1. **Generate JWT Token** using the provided script
2. **Include Bearer Token** in Authorization header for API requests
3. **Lambda Authorizer** validates token and extracts user context
4. **API Gateway** allows/denies request based on validation result

---

## 🎫 **JWT Token Generation**

### **Token Generator Script**
**Location**: `/Users/chris/climate-risk-rag-aws/generate_jwt_token.py`

### **Basic Usage**
```bash
# Generate token with defaults (test-user, solve-global, 24 hours)
python3 generate_jwt_token.py

# Generate token with custom user ID
python3 generate_jwt_token.py "john-doe"

# Generate token with custom user and organization
python3 generate_jwt_token.py "john-doe" "acme-corp"

# Generate token with custom expiration (in hours)
python3 generate_jwt_token.py "john-doe" "acme-corp" 48
```

### **Token Structure**
Generated tokens include:
- **User ID** (`sub`): Unique user identifier
- **Organization** (`org`): Organization name
- **Roles** (`roles`): Array of permissions (default: `["search", "admin"]`)
- **Token Type** (`type`): Always `"session"`
- **Issued At** (`iat`): Token creation timestamp
- **Expires** (`exp`): Token expiration timestamp

### **Example Token Generation**
```bash
$ python3 generate_jwt_token.py
============================================================
GAIP API JWT Token Generated
============================================================
User ID: test-user
Organization: solve-global
Roles: ['search', 'admin']
Valid for: 24 hours
============================================================
Bearer Token:
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXIi...
============================================================
```

---

## 🌐 **API Endpoints**

### **Base URL**
```
https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1
```

### **Available Endpoints**
| Endpoint | Method | Auth Required | Description |
|----------|--------|---------------|-------------|
| `/search` | POST | ✅ JWT Required | Solution-focused search |
| `/repository/last-update` | GET | ❌ No Auth | Repository last update info |
| `/repository/solution-count` | GET | ❌ No Auth | Solution count statistics |

### **Authentication Headers**
```http
Authorization: Bearer YOUR_JWT_TOKEN_HERE
Content-Type: application/json
```

---

## 🧪 **Test Webapp Usage**

### **Webapp Location**
**URL**: Available at S3 bucket `gaip-api-test-webapp-1758042975/index.html`

### **Setup Instructions**
1. **Open the test webapp** in your browser
2. **Enter API Endpoint**: `https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1`
3. **Generate JWT Token** using the script above
4. **Paste the Bearer Token** into the API Key field
5. **Configure search parameters** and test

### **Webapp Features**

#### **Form Sections**
- **API Configuration**: Endpoint URL and authentication token
- **Search Parameters**: Query text and result limits
- **Solution-Focused Filters**: New solution categories, risk types, geographic scope
- **Legacy Filters**: Backward compatibility filters

#### **Test Buttons**
- **Search**: Execute solution-focused search
- **Test Last Update**: Test repository metadata endpoint
- **Test Solution Count**: Test solution count endpoint
- **Clear Results**: Clear test results

#### **Preset Examples**
- **Flood Insurance Example**: Demonstrates risk reduction + insurance penetration
- **Agricultural Risk Example**: Shows drought/agricultural risk filtering
- **PPP Solutions Example**: Tests public-private partnership filtering

### **Sample Test Scenarios**

#### **Basic Search Test**
```json
{
  "query": "parametric insurance flood risk",
  "parameters": {
    "limit": 20
  }
}
```

#### **Solution-Focused Search Test**
```json
{
  "query": "agricultural insurance climate risk",
  "filters": {
    "solution_category": ["risk reduction", "insurance penetration"],
    "risk_type": ["drought", "flood", "agricultural"],
    "geographic_scope": ["ASEAN", "country"],
    "ppp_involvement": true
  },
  "parameters": {
    "limit": 50
  }
}
```

---

## 🔧 **Troubleshooting**

### **Common Issues**

#### **Token Expired Error**
```json
{
  "message": "Token expired"
}
```
**Solution**: Generate a new token using the script

#### **Invalid Token Format**
```json
{
  "message": "Invalid token format"
}
```
**Solution**: Ensure token starts with "Bearer " in the Authorization header

#### **Insufficient Permissions**
```json
{
  "message": "Insufficient permissions"
}
```
**Solution**: Ensure token includes "search" role (default in generator script)

#### **CORS Errors**
**Solution**: Ensure you're using the correct API endpoint and the webapp is served properly

### **Token Validation**
You can decode JWT tokens at [jwt.io](https://jwt.io) to inspect payload (use secret: `dev-test-secret-key-change-for-production`)

---

## 🛠️ **Development Notes**

### **JWT Secret**
- **Development**: `dev-test-secret-key-change-for-production`
- **Location**: Hardcoded in both authorizer and generator for development
- **Production**: Should be moved to AWS Secrets Manager

### **Token Expiration**
- **Default**: 24 hours
- **Configurable**: Via script parameter
- **No Refresh**: Tokens must be regenerated when expired

### **Authorization Scope**
- **Search Endpoint**: Requires JWT with "search" role
- **Repository Endpoints**: Currently no authentication required
- **Future**: May add role-based access control for different endpoint groups

---

## 📝 **API Request Examples**

### **Authenticated Search Request**
```bash
curl -X POST https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "parametric insurance flood risk",
    "filters": {
      "solution_category": ["risk reduction"],
      "risk_type": ["flood"]
    }
  }'
```

### **Repository Metadata Request (No Auth)**
```bash
curl -X GET https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/repository/last-update
```

---

## 🔄 **Token Lifecycle Management**

### **Generate New Token**
```bash
cd /Users/chris/climate-risk-rag-aws
python3 generate_jwt_token.py
```

### **Custom Token Parameters**
```bash
# Long-lived token (48 hours)
python3 generate_jwt_token.py "api-tester" "solve-global" 48

# Short-lived token (2 hours)
python3 generate_jwt_token.py "demo-user" "demo-org" 2
```

### **Token Storage**
- **Development**: Copy/paste from script output
- **Testing**: Store in test webapp form
- **Automation**: Extract programmatically from script output

---

## 📞 **Support**

### **Token Issues**
- Regenerate using the provided script
- Check token expiration time
- Verify "search" role is included

### **API Issues**
- Check endpoint URL format
- Verify request structure matches API specification
- Review CloudWatch logs for detailed error messages

### **Webapp Issues**
- Ensure all required fields are filled
- Check browser console for JavaScript errors
- Verify CORS headers are properly configured

---

**Last Updated**: September 24, 2025  
**Script Location**: `/Users/chris/climate-risk-rag-aws/generate_jwt_token.py`  
**API Endpoint**: `https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1`
