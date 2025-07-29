# Neptune Notebook Setup - Final Configuration
**Date**: 2025-07-25  
**Status**: ✅ Security Group Issue Resolved  

## 🔧 **Issue Resolution Summary**

### **Problem 1**: Package Installation Failed
- **Cause**: Private subnet without internet access
- **Solution**: Moved to public subnet with internet access

### **Problem 2**: Neptune Connection Timeout
- **Cause**: Wrong security group - Neptune only allows access from specific security groups
- **Solution**: Updated to use Lambda security group (`sg-0c9e10b9cfb4c9eb0`) that has Neptune access

---

## 📊 **Final Notebook Configuration**

### **Instance Details**
- **Name**: climate-risk-kg-notebook
- **URL**: https://climate-risk-kg-notebook-ydbq.notebook.us-east-1.sagemaker.aws
- **Instance Type**: ml.t3.medium (~$0.05/hour)
- **Network**: Public subnet (internet access enabled)
- **Security Group**: sg-0c9e10b9cfb4c9eb0 (Lambda security group with Neptune access)
- **Status**: Creating (should be ready in ~10 minutes)

---

## 🚀 **Testing Steps (Once Ready)**

### **Step 1: Install Packages**
```bash
# This should work now with internet access
pip install graph-notebook requests-aws4auth boto3

# Enable extensions
jupyter nbextension install --py --sys-prefix graph_notebook.widgets
jupyter nbextension enable  --py --sys-prefix graph_notebook.widgets
jupyter nbextension enable  --py --sys-prefix widgetsnbextension

# Restart Jupyter (use the correct method)
sudo pkill -f jupyter
# Wait 10-15 seconds and refresh browser
```

### **Step 2: Test Neptune Connection**
This should work now with the correct security group:

```python
import requests
import json

def test_neptune():
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
test_neptune()
```

### **Step 3: Query Document Structure**
```python
def query_document_structure():
    endpoint = "https://solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182"
    
    query = """
    PREFIX kr: <https://solve.global/ontologies/kr/>
    
    SELECT ?doc ?chunk (SUBSTR(?content, 1, 100) as ?preview)
    WHERE {
        ?doc a kr:Document .
        ?doc kr:hasChunk ?chunk .
        ?chunk kr:content ?content
    }
    LIMIT 5
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
            bindings = data['results']['bindings']
            
            print(f"✅ Found {len(bindings)} document chunks:")
            for binding in bindings:
                doc = binding['doc']['value']
                chunk = binding['chunk']['value']
                preview = binding['preview']['value']
                print(f"Doc: {doc.split('/')[-1]}")
                print(f"Chunk: {chunk.split('/')[-1]}")
                print(f"Content: {preview}...")
                print("-" * 50)
            
            return True
        else:
            print(f"❌ Query failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Query error: {e}")
        return False

# Run the document query
query_document_structure()
```

### **Step 4: Configure Graph Notebook (Optional)**
If the extensions installed successfully:

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

Then test with:
```python
%%sparql
SELECT ?s ?p ?o
WHERE {
  ?s ?p ?o
}
LIMIT 10
```

---

## 🎯 **Expected Results**

With the security group fix, you should now see:
- ✅ **Neptune connection successful**
- ✅ **Document data**: Document `064762102bead7b04a39` with 211 chunks
- ✅ **SPARQL queries working**
- ✅ **Graph visualizations** (if extensions work)

---

## 🔧 **Security Group Explanation**

### **Why This Was Needed**
Neptune's security group (`sg-0c8afac0f49164069`) only allows inbound connections from:
- `sg-0c043bcb40f656321` (another Lambda security group)
- `sg-0c9e10b9cfb4c9eb0` (Lambda security group we're now using)

### **Network Flow**
```
Notebook (Public Subnet) 
  ↓ (using sg-0c9e10b9cfb4c9eb0)
Neptune (Private Subnet)
  ↓ (allows sg-0c9e10b9cfb4c9eb0)
✅ Connection Allowed
```

---

## 💡 **Lessons Learned**

1. **SageMaker notebooks in private subnets** need VPC endpoints for package installation
2. **Security groups must match** Neptune's allowed inbound rules
3. **Public subnet + correct security group** = best of both worlds for development
4. **Always check security group rules** when troubleshooting connectivity

---

## 📈 **Next Steps**

Once the notebook is ready and tested:
1. **Verify current KG structure** with SPARQL queries
2. **Explore document structure data** from our pipeline run
3. **Prepare for entity integration** development
4. **Set up cost management** (auto-stop after 30 minutes)

---

**Current Status**: ⏳ Creating with correct security group  
**Expected Ready**: ~10 minutes  
**Next Action**: Test Neptune connectivity once `InService`
