# Neptune Notebook Setup Guide (Updated)
**Date**: 2025-07-25  
**Notebook Instance**: climate-risk-kg-notebook  
**Status**: Creating with Internet Access ✅  

## 🔧 **Issue Resolution**

### **Problem**: Package Installation Failed
The initial notebook was in a private subnet without internet access, preventing pip installations.

### **Solution**: Recreated with Internet Access
- **New URL**: https://climate-risk-kg-notebook-eks6.notebook.us-east-1.sagemaker.aws
- **Network**: Public subnet with internet access
- **Security**: Same security group (can still access Neptune)

---

## 📊 **Updated Notebook Details**

### **Instance Configuration**
- **Name**: climate-risk-kg-notebook
- **Instance Type**: ml.t3.medium (~$0.05/hour)
- **Storage**: 20GB EBS
- **Network**: Public subnet (internet access enabled)
- **URL**: https://climate-risk-kg-notebook-eks6.notebook.us-east-1.sagemaker.aws
- **Status**: Creating (should be ready in ~10 minutes)

---

## 🚀 **Testing Steps (Once Ready)**

### **Step 1: Verify Internet Access**
Once the notebook status is `InService`, open a terminal and test:

```bash
# Test internet connectivity
ping -c 3 google.com

# Test PyPI access
pip --version
```

### **Step 2: Install Graph Notebook Package**
```bash
# Install the graph-notebook package (should work now!)
pip install graph-notebook

# Install additional dependencies
pip install requests-aws4auth boto3

# Enable the graph notebook extensions
jupyter nbextension install --py --sys-prefix graph_notebook.widgets
jupyter nbextension enable  --py --sys-prefix graph_notebook.widgets
jupyter nbextension enable  --py --sys-prefix widgetsnbextension

# Restart Jupyter to load extensions
sudo systemctl restart jupyter
```

### **Step 3: Configure Neptune Connection**
Create a new notebook and run:

```python
%graph_notebook_config
```

Configure with:
```json
{
  "host": "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com",
  "port": 8182,
  "auth_mode": "DEFAULT",
  "load_from_s3_arn": "",
  "ssl": true,
  "aws_region": "us-east-1"
}
```

### **Step 4: Test Neptune Connection**
```python
%%sparql
SELECT ?s ?p ?o
WHERE {
  ?s ?p ?o
}
LIMIT 10
```

### **Step 5: Verify Document Structure Data**
Since we processed a document earlier, you should see data:

```python
%%sparql
PREFIX kr: <https://solve.global/ontologies/kr/>

SELECT (COUNT(*) as ?triples)
WHERE {
  ?s ?p ?o
}
```

```python
%%sparql
PREFIX kr: <https://solve.global/ontologies/kr/>

SELECT ?doc ?chunk
WHERE {
  ?doc a kr:Document .
  ?doc kr:hasChunk ?chunk
}
LIMIT 10
```

---

## 🔍 **Expected Results**

Based on our successful pipeline run, you should see:
- **Total triples**: Several thousand (document structure + chunks)
- **Document ID**: `064762102bead7b04a39`
- **Chunks**: 211 chunks from the processed document
- **Graph visualization**: Available through graph-notebook widgets

---

## 💡 **Alternative Testing (If Still Issues)**

If graph-notebook still has issues, you can test Neptune directly:

```python
import boto3
import requests
import json

def test_neptune_sparql():
    endpoint = "https://solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182"
    
    query = """
    SELECT (COUNT(*) as ?count)
    WHERE {
        ?s ?p ?o
    }
    """
    
    try:
        response = requests.post(
            f"{endpoint}/sparql",
            data={'query': query},
            headers={'Accept': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            count = data['results']['bindings'][0]['count']['value']
            print(f"✅ Neptune connection successful!")
            print(f"Total triples in graph: {count}")
            return True
        else:
            print(f"❌ Query failed: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

# Test the connection
test_neptune_sparql()
```

---

## 🛠️ **Troubleshooting**

### **If Package Installation Still Fails**
```bash
# Check internet connectivity
curl -I https://pypi.org/

# Try alternative package sources
pip install --index-url https://pypi.org/simple/ graph-notebook

# Check DNS resolution
nslookup pypi.org
```

### **If Neptune Connection Fails**
```python
# Test basic AWS connectivity
import boto3
client = boto3.client('neptune', region_name='us-east-1')
try:
    clusters = client.describe_db_clusters()
    print("✅ AWS API access working")
    print(f"Neptune cluster status: {clusters['DBClusters'][0]['Status']}")
except Exception as e:
    print(f"❌ AWS API error: {e}")
```

---

## 📈 **Next Steps**

### **Once Working**
1. **Verify current KG structure** with SPARQL queries
2. **Test graph visualizations** with sample queries
3. **Prepare for entity integration** verification
4. **Set up auto-stop** to manage costs (30 minutes recommended)

### **Cost Management**
```bash
# Stop notebook when not in use
aws sagemaker stop-notebook-instance \
  --notebook-instance-name climate-risk-kg-notebook \
  --profile solve-global

# Start when needed
aws sagemaker start-notebook-instance \
  --notebook-instance-name climate-risk-kg-notebook \
  --profile solve-global
```

---

**Current Status**: ⏳ Creating with internet access  
**Expected Ready**: ~10 minutes  
**Next Action**: Test package installation once `InService`
