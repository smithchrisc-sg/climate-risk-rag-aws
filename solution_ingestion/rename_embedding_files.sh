#!/bin/bash

# Rename embedding files to include "_embedding" suffix
# From: sol_abc123_chunk_0002.json
# To:   sol_abc123_chunk_0002_embedding.json

echo "Renaming embedding files to include '_embedding' suffix..."

cd output_data/kr-dl-embeddings/data-lake

count=0
for dir in sol_*; do
    if [ -d "$dir" ]; then
        cd "$dir"
        for file in *.json; do
            if [ -f "$file" ]; then
                # Extract the base name without .json extension
                base_name="${file%.json}"
                # Create new name with _embedding suffix
                new_name="${base_name}_embedding.json"
                
                if [ "$file" != "$new_name" ]; then
                    mv "$file" "$new_name"
                    count=$((count + 1))
                fi
            fi
        done
        cd ..
    fi
done

echo "Renamed $count embedding files"
echo "Done!"
