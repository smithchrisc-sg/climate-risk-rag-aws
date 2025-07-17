#!/bin/bash

# Create temporary directories
TEMP_DIR=$(mktemp -d)
EXTRACT_DIR="$TEMP_DIR/extract"
mkdir -p "$EXTRACT_DIR"

# Download the current layer
echo "Downloading current layer..."
LAYER_URL=$(aws lambda get-layer-version --layer-name climate-risk-core-utilities --version-number 8 --query 'Content.Location' --output text)
curl -s "$LAYER_URL" -o "$TEMP_DIR/layer.zip"

# Extract the layer
echo "Extracting layer..."
unzip -q "$TEMP_DIR/layer.zip" -d "$EXTRACT_DIR"

# Create the fixed method
cat > "$TEMP_DIR/fixed_method.py" << 'EOL'
    def _split_into_sentences(self, text: str) -> List[str]:
        """Enhanced sentence splitting with regex that works in Python 3.11"""
        import re
        
        # Instead of using a variable-width look-behind assertion, we'll use a different approach
        # First, split on potential sentence boundaries
        potential_sentences = re.split(r'\s*[.!?]+\s+(?=[A-Z])', text)
        
        # Then filter out false positives (where the split happened after an abbreviation)
        sentences = []
        abbreviations = ['Mr', 'Mrs', 'Ms', 'Dr', 'Prof', 'Sr', 'Jr', 'vs', 'etc', 'Inc', 'Corp', 'Ltd', 'Co', 
                         'St', 'Ave', 'Blvd', 'Rd', 'Fig', 'Table', 'Ch', 'Sec', 'Vol', 'No', 'pp', 'cf', 'i.e', 'e.g', 'et al']
        
        for i, s in enumerate(potential_sentences):
            if i == 0:
                # First segment is always included
                sentences.append(s.strip())
            else:
                # Check if the previous segment ends with an abbreviation
                prev_segment = potential_sentences[i-1]
                is_abbreviation = False
                
                for abbr in abbreviations:
                    if prev_segment.strip().endswith(abbr):
                        is_abbreviation = True
                        # Combine with previous segment
                        sentences[-1] = sentences[-1] + '.' + s.strip()
                        break
                
                if not is_abbreviation:
                    sentences.append(s.strip())
        
        # Clean up sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Handle edge cases where splitting failed
        if len(sentences) == 1 and len(text) > self.max_chunk_size:
            # Fallback to simpler splitting
            sentences = re.split(r'[.!?]+\s+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
EOL

# Find the file to modify
CHUNKER_FILE="$EXTRACT_DIR/python/structured_chunking_smart_complete.py"

# Create a backup
cp "$CHUNKER_FILE" "$CHUNKER_FILE.bak"

# Replace the method using awk
awk -v fixed_method="$(cat $TEMP_DIR/fixed_method.py)" '
BEGIN { in_method = 0; }
/def _split_into_sentences/ { in_method = 1; print fixed_method; next; }
/return sentences/ { if (in_method) { in_method = 0; next; } }
{ if (!in_method) print; }
' "$CHUNKER_FILE.bak" > "$CHUNKER_FILE"

# Create a new zip file
echo "Creating new layer zip..."
cd "$EXTRACT_DIR"
zip -r "$TEMP_DIR/new_layer.zip" .

# Publish the new layer
echo "Publishing new layer..."
aws lambda publish-layer-version \
  --layer-name climate-risk-core-utilities \
  --description "Fixed regex pattern in SmartStructuredChunker._split_into_sentences" \
  --zip-file "fileb://$TEMP_DIR/new_layer.zip" \
  --compatible-runtimes python3.11

# Get the new version number
NEW_VERSION=$(aws lambda list-layer-versions --layer-name climate-risk-core-utilities --max-items 1 --query 'LayerVersions[0].Version' --output text)
echo "New layer version: $NEW_VERSION"

# Update the Lambda functions
for FUNC in "text-chunker-pipeline" "solve-global-kr-text-chunker-phase1"; do
  echo "Updating $FUNC..."
  
  # Get current layers
  LAYERS=$(aws lambda get-function --function-name "$FUNC" --query 'Configuration.Layers[*].Arn' --output text)
  
  # Replace the climate-risk-core-utilities layer with the new version
  NEW_LAYERS=""
  for LAYER in $LAYERS; do
    if [[ "$LAYER" == *"climate-risk-core-utilities:"* && "$LAYER" != *"climate-risk-core-utilities-db:"* ]]; then
      NEW_LAYER="arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities:$NEW_VERSION"
      NEW_LAYERS="$NEW_LAYERS $NEW_LAYER"
    else
      NEW_LAYERS="$NEW_LAYERS $LAYER"
    fi
  done
  
  # Update the function
  aws lambda update-function-configuration \
    --function-name "$FUNC" \
    --layers $NEW_LAYERS
done

# Clean up
rm -rf "$TEMP_DIR"

echo "Done!"
