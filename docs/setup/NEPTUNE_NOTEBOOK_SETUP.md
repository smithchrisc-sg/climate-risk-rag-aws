# Neptune Notebook Setup Guide
**Date**: 2025-07-25  
**Notebook Instance**: climate-risk-kg-notebook  
**Purpose**: SPARQL querying and KG visualization for entity verification  

## 📊 **Notebook Details**

### **Instance Configuration**
- **Name**: climate-risk-kg-notebook
- **Instance Type**: ml.t3.medium (~$0.05/hour)
- **Storage**: 20GB EBS
- **Network**: Private subnet (no internet access)
- **URL**: https://climate-risk-kg-notebook-rsd5.notebook.us-east-1.sagemaker.aws

### **Cost Optimization**
- **Auto-stop**: Configure after first access (recommended: 30 minutes)
- **Expected Monthly Cost**: $10-20 with proper usage
- **Start/Stop**: Use AWS CLI or console as needed

---

## 🚀 **Initial Setup (Run Once)**

### **Step 1: Install Graph Notebook Package**
Once the notebook is `InService`, open a terminal and run:

```bash
# Install the graph-notebook package
pip install graph-notebook

# Install additional dependencies
pip install requests-aws4auth boto3

# Enable the graph notebook extension
jupyter nbextension install --py --sys-prefix graph_notebook.widgets
jupyter nbextension enable  --py --sys-prefix graph_notebook.widgets
jupyter nbextension enable  --py --sys-prefix widgetsnbextension

# Restart Jupyter (from terminal)
sudo systemctl restart jupyter
```

### **Step 2: Configure Neptune Connection**
Create a new notebook and run:

```python
%graph_notebook_config
```

Then configure with:
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

### **Step 3: Test Connection**
```python
%%sparql
SELECT ?s ?p ?o
WHERE {
  ?s ?p ?o
}
LIMIT 10
```

---

## 🔍 **Verification Queries for Entity Integration**

### **Check Current Graph Content**
```sparql
%%sparql
SELECT (COUNT(*) as ?triples)
WHERE {
  ?s ?p ?o
}
```

### **List All Entity Types**
```sparql
%%sparql
SELECT DISTINCT ?type (COUNT(?entity) as ?count)
WHERE {
  ?entity a ?type
}
GROUP BY ?type
ORDER BY DESC(?count)
```

### **View Document Structure**
```sparql
%%sparql
PREFIX kr: <https://solve.global/ontologies/kr/>

SELECT ?doc ?chunk ?content
WHERE {
  ?doc a kr:Document .
  ?doc kr:hasChunk ?chunk .
  ?chunk kr:content ?content
}
LIMIT 10
```

### **Check for Entities in Documents**
```sparql
%%sparql
PREFIX kr: <https://solve.global/ontologies/kr/>

SELECT ?doc ?entity ?entityType ?mention
WHERE {
  ?doc a kr:Document .
  ?doc kr:hasEntity ?entity .
  ?entity a ?entityType .
  ?entity kr:mentionedAs ?mention
}
LIMIT 20
```

### **Entity Relationships**
```sparql
%%sparql
PREFIX kr: <https://solve.global/ontologies/kr/>

SELECT ?entity1 ?relationship ?entity2
WHERE {
  ?entity1 ?relationship ?entity2 .
  ?entity1 a kr:Entity .
  ?entity2 a kr:Entity .
}
LIMIT 15
```

### **Document-Entity Co-occurrence**
```sparql
%%sparql
PREFIX kr: <https://solve.global/ontologies/kr/>

SELECT ?doc ?entity1 ?entity2
WHERE {
  ?doc kr:hasEntity ?entity1 .
  ?doc kr:hasEntity ?entity2 .
  FILTER(?entity1 != ?entity2)
}
LIMIT 10
```

---

## 🎯 **Entity Integration Verification Checklist**

### **After Entity Processing Implementation**
- [ ] **Entities Extracted**: Verify entities are being extracted from documents
- [ ] **Entity Types**: Check that different entity types are properly classified
- [ ] **Entity Relationships**: Confirm relationships between entities are captured
- [ ] **Document Links**: Verify entities are properly linked to source documents
- [ ] **Knowledge Graph Structure**: Ensure proper ontology structure is maintained

### **Sample Verification Workflow**
1. **Process a test document** through the pipeline
2. **Check document structure** is created properly
3. **Verify entities are extracted** and stored in Neptune
4. **Validate entity relationships** are captured
5. **Test entity search queries** work as expected

---

## 💡 **Useful SPARQL Patterns**

### **Find Documents Containing Specific Entities**
```sparql
%%sparql
PREFIX kr: <https://solve.global/ontologies/kr/>

SELECT ?doc ?title
WHERE {
  ?doc a kr:Document .
  ?doc kr:title ?title .
  ?doc kr:hasEntity ?entity .
  ?entity kr:mentionedAs "climate change" .
}
```

### **Entity Co-occurrence Analysis**
```sparql
%%sparql
PREFIX kr: <https://solve.global/ontologies/kr/>

SELECT ?entity1 ?entity2 (COUNT(?doc) as ?cooccurrence)
WHERE {
  ?doc kr:hasEntity ?entity1 .
  ?doc kr:hasEntity ?entity2 .
  FILTER(?entity1 != ?entity2)
}
GROUP BY ?entity1 ?entity2
ORDER BY DESC(?cooccurrence)
LIMIT 20
```

### **Most Mentioned Entities**
```sparql
%%sparql
PREFIX kr: <https://solve.global/ontologies/kr/>

SELECT ?entity ?mention (COUNT(?doc) as ?frequency)
WHERE {
  ?doc kr:hasEntity ?entity .
  ?entity kr:mentionedAs ?mention .
}
GROUP BY ?entity ?mention
ORDER BY DESC(?frequency)
LIMIT 15
```

---

## 🛠️ **Notebook Management**

### **Start/Stop Commands**
```bash
# Start notebook
aws sagemaker start-notebook-instance \
  --notebook-instance-name climate-risk-kg-notebook \
  --profile solve-global

# Stop notebook (to save costs)
aws sagemaker stop-notebook-instance \
  --notebook-instance-name climate-risk-kg-notebook \
  --profile solve-global

# Check status
aws sagemaker describe-notebook-instance \
  --notebook-instance-name climate-risk-kg-notebook \
  --profile solve-global
```

### **Cost Management**
- **Stop when not in use**: Saves ~$0.05/hour
- **Auto-stop configuration**: Set to 30 minutes of inactivity
- **Monitor usage**: Check AWS Cost Explorer regularly

---

## 🔧 **Troubleshooting**

### **Common Issues**
1. **Connection fails**: Check Neptune security group allows notebook access
2. **Queries timeout**: Increase query timeout in configuration
3. **No data returned**: Verify TTL files have been loaded into Neptune
4. **Visualization issues**: Ensure graph-notebook widgets are properly installed

### **Debug Commands**
```python
# Test Neptune connectivity
import boto3
client = boto3.client('neptune', region_name='us-east-1')
print(client.describe_db_clusters()['DBClusters'][0]['Status'])

# Check graph-notebook installation
!pip list | grep graph-notebook

# Test SPARQL endpoint
%%sparql
SELECT ?g (COUNT(*) as ?triples)
WHERE {
  GRAPH ?g { ?s ?p ?o }
}
GROUP BY ?g
```

---

## 📈 **Next Steps**

### **Once Entity Integration is Complete**
1. **Test entity extraction** with sample documents
2. **Verify knowledge graph structure** matches expectations
3. **Optimize SPARQL queries** for performance
4. **Create visualization dashboards** for entity relationships
5. **Document entity integration patterns** for team reference

### **Advanced Usage**
- **Custom visualizations**: Create specialized graph views
- **Query optimization**: Tune SPARQL queries for large datasets
- **Export capabilities**: Extract data for external analysis
- **Integration testing**: Validate end-to-end entity pipeline

---

**Setup Status**: ⏳ Notebook creating (check status with AWS CLI)  
**Next Action**: Wait for `InService` status, then run initial setup  
**Estimated Setup Time**: 10-15 minutes after notebook is ready
