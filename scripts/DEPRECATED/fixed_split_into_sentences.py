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
