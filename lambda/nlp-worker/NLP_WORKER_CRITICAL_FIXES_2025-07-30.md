# NLP WORKER CRITICAL FIXES - 2025-07-30

## 🚨 **CRITICAL ISSUE DISCOVERED**

The nlp-worker's entity and keyphrase mapping logic was **fundamentally broken** due to changes in chunk structure for hierarchical chunking and semantic schema v3.1.

## ❌ **PROBLEMS IDENTIFIED**

### **Problem 1: Wrong Sort Key**
```python
# BROKEN CODE:
chunks.sort(key=lambda x: x.get('position', 0))
```
- Current chunk structure doesn't have `position` field
- Should use `chunk_index` instead
- Chunks were not being sorted correctly

### **Problem 2: Incorrect Offset Calculation**
```python
# BROKEN LOGIC:
current_offset = 0
for chunk in chunks:
    text = chunk.get('text', '')
    chunk_offsets.append({
        'start': current_offset,
        'end': current_offset + len(text),
    })
    current_offset += len(text)  # WRONG!
```

**Why this was wrong:**
- Assumes chunks are sequential text segments that can be concatenated
- With hierarchical chunking, chunks may overlap or have gaps
- Parent chunks may contain child chunks
- Creates a **fictional document** that doesn't match what Comprehend analyzed

### **Problem 3: Comprehend Input Mismatch**
- **Comprehend analyzes**: Original full document text (from nlp-initiator)
- **Mapping logic used**: Reconstructed text from concatenated chunks
- **Result**: Entity/keyphrase offsets couldn't be mapped correctly

## ✅ **CORRECTED APPROACH**

### **New Architecture**
1. **Load Original Text**: Get the exact text that nlp-initiator sent to Comprehend
2. **Find Chunk Positions**: Locate where each chunk's text appears in the original document
3. **Map Using Original Offsets**: Use entity/keyphrase offsets relative to original text
4. **Handle Hierarchical Structure**: Support overlapping chunks and parent-child relationships

### **Key Changes Made**

#### **1. Added Text Bucket Configuration**
```python
self.text_bucket = os.environ.get('TEXT_BUCKET',
                                 'solve-global-kr-text-861276078413-us-east-1')
```

#### **2. New Function: `load_original_document_text()`**
```python
def load_original_document_text(self, doc_id: str) -> str:
    """Load the original document text that was sent to Comprehend"""
    text_key = f"text/{doc_id}.txt"
    # Load from S3 text bucket
```

#### **3. New Function: `find_chunk_positions_in_original_text()`**
```python
def find_chunk_positions_in_original_text(self, chunks: List[Dict], original_text: str) -> List[Dict]:
    """Find where each chunk's text appears in the original document"""
    # Uses string.find() to locate chunk text in original document
    # Returns positions with start_offset, end_offset relative to original
```

#### **4. Completely Rewritten `map_results_to_chunks()`**
```python
def map_results_to_chunks(self, comprehend_results: Dict[str, List], chunks: List[Dict], doc_id: str) -> Dict[str, List]:
    """CORRECTED: Map using original document positions"""
    # 1. Load original document text
    # 2. Find chunk positions in original text
    # 3. Map entities/keyphrases using original offsets
    # 4. Support hierarchical chunk structure
```

#### **5. Enhanced Mapping Output**
New mapping includes hierarchical metadata:
```python
{
    'chunk_id': chunk_pos['chunk_id'],
    'chunk_index': chunk_pos['chunk_index'],
    'section_type': chunk_pos['section_type'],
    'hierarchy_level': chunk_pos['hierarchy_level'],
    'parent_chunk_id': chunk_pos['parent_chunk_id'],
    'entity': entity_text,
    'type': entity.get('type', ''),
    'score': entity.get('score', 0),
    'original_begin_offset': entity_start,  # NEW: Original document offset
    'original_end_offset': entity_end,      # NEW: Original document offset
    'chunk_relative_begin': relative_start, # Relative to chunk
    'chunk_relative_end': relative_end      # Relative to chunk
}
```

## 🔧 **TECHNICAL IMPLEMENTATION**

### **Chunk Structure Compatibility**
The corrected code now properly handles the current hierarchical chunk structure:
- `chunk_id`: Unique identifier
- `chunk_index`: Sequential index for sorting
- `text`: Chunk content
- `section_type`: Document section type (paragraph, header, etc.)
- `hierarchy_level`: Hierarchical level in document structure
- `parent_chunk_id`: Parent chunk for hierarchical relationships
- `child_chunk_ids`: Child chunks (if any)

### **Error Handling**
- Graceful fallback if original text can't be loaded
- Warning logs for entities/keyphrases that can't be mapped
- Empty results returned instead of crashing

### **Performance Considerations**
- Efficient string searching using `str.find()`
- Sorted chunk positions for optimal mapping
- Minimal memory overhead

## 🧪 **TESTING REQUIREMENTS**

### **Critical Test Cases**
1. **Basic Mapping**: Simple document with non-overlapping chunks
2. **Hierarchical Chunks**: Document with parent-child chunk relationships
3. **Overlapping Chunks**: Chunks with semantic overlap
4. **Edge Cases**: 
   - Entities spanning multiple chunks
   - Chunks not found in original text
   - Empty chunks or missing text

### **Validation Steps**
1. **Deploy Updated Code**: Update nlp-worker Lambda function
2. **Test with Known Document**: Use document that previously failed mapping
3. **Verify Mapping Accuracy**: Check that entities/keyphrases map to correct chunks
4. **Check Hierarchical Data**: Ensure parent_chunk_id and hierarchy_level are preserved

## 🚨 **DEPLOYMENT URGENCY**

This is a **CRITICAL FIX** that must be deployed before any NLP processing:
- Current mapping logic produces incorrect results
- Entity/keyphrase data is being lost or misattributed
- Hierarchical chunk relationships are not being preserved
- Search and analysis functionality is compromised

## 📋 **DEPLOYMENT CHECKLIST**

- [ ] **Update Environment Variables**: Add TEXT_BUCKET configuration
- [ ] **Deploy Lambda Code**: Update nlp-worker function
- [ ] **Test with Sample Document**: Verify mapping works correctly
- [ ] **Monitor CloudWatch Logs**: Check for mapping warnings/errors
- [ ] **Validate Database Results**: Ensure entities/keyphrases are correctly stored

## 🎯 **SUCCESS CRITERIA**

- ✅ Entities map to correct chunks based on original document positions
- ✅ Keyphrases map to correct chunks based on original document positions  
- ✅ Hierarchical chunk metadata is preserved in mapping results
- ✅ No mapping errors in CloudWatch logs
- ✅ Database contains accurate entity/keyphrase to chunk relationships

---

**This fix resolves a fundamental architectural flaw that was causing incorrect entity/keyphrase mapping. It's essential for the accuracy of the entire NLP processing pipeline.**
