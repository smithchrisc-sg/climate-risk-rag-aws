#!/usr/bin/env bash
set -uo pipefail

# ------ Config ------
IN="${1:-all-geonames-rdf-fixed.rdf}"     # input concatenated RDF/XML
OUT_BASE="${2:-country-features}"         # base name for outputs
PRETTY="$OUT_BASE-pretty.ttl"
RAW_TTL="$OUT_BASE.ttl"
RAW_SUBJ="keep_subjects.txt"
WRITE_GZIP=${WRITE_GZIP:-1}               # set 0 to skip .gz
SHOW_PROGRESS=${SHOW_PROGRESS:-0}         # set 1 to show pv progress
KEEP_RAW=${KEEP_RAW:-0}                   # set 1 to keep $RAW_TTL
# --------------------

# Prefix header we want in the final pretty Turtle
prefixes() {
  cat <<'EOF'
@prefix gn:         <http://www.geonames.org/ontology#> .
@prefix wgs84_pos:  <http://www.w3.org/2003/01/geo/wgs84_pos#> .
@prefix rdfs:       <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rdf:        <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix cc:         <http://creativecommons.org/ns#> .
@prefix dcterms:    <http://purl.org/dc/terms/> .
@prefix foaf:       <http://xmlns.com/foaf/0.1/> .
EOF
}

# Stream one valid RDF/XML by:
# - printing the first <rdf:RDF ...> tag once (header only),
# - stripping any <rdf:RDF ...> and </rdf:RDF> in fragments but KEEPING the rest of the line,
# - removing XML prologs and bare URL lines,
# - closing with one </rdf:RDF>.
stream_merged() {
  awk '
  BEGIN { printed_header=0 }
  {
    line=$0

    # Drop bare URL lines like "https://sws.geonames.org/94/"
    if (line ~ /^[[:space:]]*https?:\/\/[^[:space:]]+[[:space:]]*$/) next

    # Remove XML prolog if present (can appear anywhere in these one-line fragments)
    gsub(/<\?xml[^>]*\?>/,"",line)

    # Handle opening <rdf:RDF ...>
    if (!printed_header && line ~ /<rdf:RDF[^>]*>/) {
      match(line,/<rdf:RDF[^>]*>/)
      header=substr(line,RSTART,RLENGTH)
      print header
      printed_header=1
      # Remove just the header tag; keep remainder of feature content
      line = substr(line,1,RSTART-1) substr(line,RSTART+RLENGTH)
    } else {
      # For subsequent fragments, strip any <rdf:RDF ...>; keep remainder
      gsub(/<rdf:RDF[^>]*>/,"",line)
    }

    # Remove any closing tags inside fragments
    gsub(/<\/rdf:RDF>/,"",line)

    if (line ~ /[^[:space:]]/) print line
  }
  END { print "</rdf:RDF>" }
  ' "$IN"
}

# Helper to optionally show throughput using pv
maybe_pv() {
  if [ "$SHOW_PROGRESS" -eq 1 ] && command -v pv >/dev/null 2>&1; then
    pv
  else
    cat
  fi
}

echo "=== Pass 1: Collecting Country (A.PCLI) subjects ==="
stream_merged \
| maybe_pv \
| ( riot --syntax=rdfxml --output=ntriples 2>riot-pass1.err || true ) \
| awk '$2 ~ /geonames\.org\/ontology#featureCode>$/ && $3 ~ /#A\.PCLI>$/ { print $1 }' \
| sort -u > "$RAW_SUBJ"

COUNT=$(wc -l < "$RAW_SUBJ" | tr -d " ")
echo "Country subjects to keep: $COUNT"
if [ "$COUNT" -eq 0 ]; then
  echo "No matching country subjects found. Showing a few parsed featureCode triples:"
  stream_merged \
  | ( riot --syntax=rdfxml --output=ntriples 2>/dev/null || true ) \
  | awk '$2 ~ /geonames\.org\/ontology#featureCode>/' \
  | head -n 10
  exit 1
fi

echo "=== Pass 2: Filtering triples for kept country subjects → Turtle (raw) ==="
stream_merged \
| maybe_pv \
| ( riot --syntax=rdfxml --output=ntriples 2>riot-pass2.err || true ) \
| awk 'NR==FNR { keep[$1]=1; next } (keep[$1])' "$RAW_SUBJ" - \
| riot --syntax=ntriples --output=turtle > "$RAW_TTL"

if [ ! -s "$RAW_TTL" ]; then
  echo "No Turtle written — check riot-pass2.err."
  exit 1
fi
echo "Wrote raw Turtle: $RAW_TTL"

echo "=== Pretty-printing with prefixes ==="
{ prefixes; cat "$RAW_TTL"; } \
| riot --syntax=turtle --output=turtle > "$PRETTY"

echo "Wrote pretty Turtle: $PRETTY"

if [ "$WRITE_GZIP" -eq 1 ]; then
  gzip -f -9 -k "$PRETTY"
  echo "Also wrote: $PRETTY.gz"
fi

if [ "$KEEP_RAW" -ne 1 ]; then
  rm -f "$RAW_TTL"
fi

echo "Done. Country subjects kept: $COUNT"
