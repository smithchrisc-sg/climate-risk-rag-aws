"""
Smart Structured Chunking Module - Part 2
Enhanced detection methods and smart chunking logic
"""

    def _is_header_smart(self, text: str, line: Dict, all_lines: List[Dict], index: int) -> bool:
        """Enhanced header detection using multiple signals"""
        
        # Pattern matching
        import re
        for pattern in self.header_patterns:
            if re.match(pattern, text):
                return True
        
        # Font size analysis (enhanced with context)
        bbox = line['bounding_box']
        line_height = bbox.get('Height', 0)
        
        # Compare with surrounding lines (more context)
        surrounding_heights = []
        for i in range(max(0, index-2), min(len(all_lines), index+3)):
            if i != index:
                surrounding_heights.append(all_lines[i]['bounding_box'].get('Height', 0))
        
        if surrounding_heights:
            avg_height = sum(surrounding_heights) / len(surrounding_heights)
            # Significantly larger text is likely a header
            if line_height > avg_height * 1.3:
                return True
        
        # Positioning analysis (enhanced)
        left_margin = bbox.get('Left', 0)
        
        # Very left-aligned and short text might be header
        if left_margin < 0.1 and len(text) < 100 and len(text.split()) <= 10:
            return True
        
        # All caps and reasonable length might be header
        if text.isupper() and 3 <= len(text.split()) <= 12:
            return True
        
        # Check for common header words
        header_indicators = ['chapter', 'section', 'introduction', 'conclusion', 'summary', 'overview']
        if any(indicator in text.lower() for indicator in header_indicators):
            if len(text.split()) <= 8:
                return True
        
        return False
    
    def _determine_header_level_smart(self, text: str, line: Dict, all_lines: List[Dict], index: int) -> int:
        """Enhanced header hierarchy level determination"""
        import re
        
        # Check for numbered sections with more patterns
        if re.match(r'^\d+\.?\s+', text):
            return 2
        elif re.match(r'^\d+\.\d+\.?\s+', text):
            return 3
        elif re.match(r'^\d+\.\d+\.\d+\.?\s+', text):
            return 4
        
        # Check for Roman numerals
        if re.match(r'^[IVX]+\.?\s+', text):
            return 2
        
        # Check for letter sections
        if re.match(r'^[A-Z]\.?\s+', text):
            return 3
        
        # Font size-based with enhanced logic
        line_height = line['bounding_box'].get('Height', 0)
        
        # Calculate relative size compared to document average
        all_heights = [l['bounding_box'].get('Height', 0) for l in all_lines]
        avg_height = sum(all_heights) / len(all_heights) if all_heights else 0.02
        
        relative_size = line_height / avg_height if avg_height > 0 else 1
        
        if relative_size > 1.8:  # Very large text
            return 1
        elif relative_size > 1.4:  # Large text
            return 2
        elif relative_size > 1.1:  # Slightly larger text
            return 3
        else:
            return 4
    
    def _is_list_item_smart(self, text: str, line: Dict, all_lines: List[Dict], index: int) -> bool:
        """Enhanced list item detection"""
        import re
        
        # Standard list patterns
        for pattern in self.list_patterns:
            if re.match(pattern, text):
                return True
        
        # Check for indented text that might be list items
        left_margin = line['bounding_box'].get('Left', 0)
        
        # Compare with surrounding lines to detect indentation
        if index > 0:
            prev_margin = all_lines[index - 1]['bounding_box'].get('Left', 0)
            if left_margin > prev_margin + 0.02:  # Indented
                # Check if it starts with common list indicators
                if re.match(r'^\s*[•▪▫◦‣⁃]\s+', text) or re.match(r'^\s*[→➤➢]\s+', text):
                    return True
        
        return False
    
    def _is_table_content_smart(self, text: str, line: Dict, all_lines: List[Dict], index: int) -> bool:
        """Enhanced table content detection"""
        
        # Multiple tab-separated values
        if '\t' in text and len(text.split('\t')) > 2:
            return True
        
        # Multiple spaces suggesting columns (enhanced)
        import re
        if re.search(r'\s{3,}', text) and len(text.split()) > 3:
            # Check if surrounding lines also look like table content
            table_like_count = 0
            for i in range(max(0, index-1), min(len(all_lines), index+2)):
                if i != index:
                    other_text = all_lines[i]['text']
                    if re.search(r'\s{3,}', other_text) and len(other_text.split()) > 2:
                        table_like_count += 1
            
            if table_like_count >= 1:  # At least one surrounding line looks table-like
                return True
        
        # Check for common table patterns
        table_patterns = [
            r'^\s*\|\s*.*\s*\|\s*$',  # Pipe-separated
            r'.*\s+\d+\s+\d+.*',      # Numbers in columns
            r'.*\s+\$\d+.*',          # Currency values
        ]
        
        for pattern in table_patterns:
            if re.match(pattern, text):
                return True
        
        return False
    
    def _is_caption_smart(self, text: str, line: Dict) -> bool:
        """Enhanced caption detection"""
        import re
        caption_patterns = [
            r'^Figure\s+\d+',
            r'^Table\s+\d+',
            r'^Chart\s+\d+',
            r'^Graph\s+\d+',
            r'^Image\s+\d+',
            r'^Exhibit\s+\d+',
        ]
        
        for pattern in caption_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _merge_bounding_boxes(self, bbox1: Dict, bbox2: Dict) -> Dict:
        """Merge two bounding boxes to encompass both"""
        if not bbox1:
            return bbox2
        if not bbox2:
            return bbox1
        
        # Calculate merged bounding box
        left = min(bbox1.get('Left', 0), bbox2.get('Left', 0))
        top = min(bbox1.get('Top', 0), bbox2.get('Top', 0))
        
        right1 = bbox1.get('Left', 0) + bbox1.get('Width', 0)
        right2 = bbox2.get('Left', 0) + bbox2.get('Width', 0)
        right = max(right1, right2)
        
        bottom1 = bbox1.get('Top', 0) + bbox1.get('Height', 0)
        bottom2 = bbox2.get('Top', 0) + bbox2.get('Height', 0)
        bottom = max(bottom1, bottom2)
        
        return {
            'Left': left,
            'Top': top,
            'Width': right - left,
            'Height': bottom - top
        }
    
    def _create_smart_structured_chunks(self, sections: List[DocumentSection]) -> List[StructuredChunk]:
        """Create chunks with smart overlap strategy"""
        chunks = []
        
        for i, section in enumerate(sections):
            # Handle different section types with smart strategies
            if section.section_type == SectionType.TABLE and self.preserve_tables:
                # Tables as complete units - no overlap
                chunk = self._create_table_chunk(section)
                chunks.append(chunk)
                
            elif section.section_type == SectionType.LIST and self.preserve_lists:
                # Lists as complete units - no overlap
                chunk = self._create_list_chunk(section)
                chunks.append(chunk)
                
            elif section.section_type in [SectionType.TITLE, SectionType.HEADER, SectionType.SUBHEADER]:
                # Headers with natural context - no artificial overlap
                if self.header_context:
                    chunk = self._create_header_with_context(section, sections, i)
                else:
                    chunk = self._create_header_chunk(section)
                chunks.append(chunk)
                
            elif section.section_type == SectionType.PARAGRAPH:
                # Paragraphs with smart overlap only when splitting
                para_chunks = self._split_paragraph_with_smart_overlap(section, sections, i)
                chunks.extend(para_chunks)
                
            else:
                # Default chunk creation
                chunk = self._create_default_chunk(section)
                chunks.append(chunk)
        
        return chunks
    
    def _create_table_chunk(self, section: DocumentSection) -> StructuredChunk:
        """Create a chunk for table content - complete unit, no overlap"""
        return StructuredChunk(
            text=section.text,
            chunk_type="table",
            hierarchy_level=section.hierarchy_level,
            page_number=section.page_number,
            section_context="table_data",
            word_count=len(section.text.split()),
            sentence_count=section.text.count('.') + section.text.count('!') + section.text.count('?'),
            bounding_box=section.bounding_box,
            metadata={
                'section_type': section.section_type.value,
                'confidence': section.confidence,
                'preserve_structure': True,
                'overlap_strategy': 'none',
                'smart_chunking': True
            }
        )
    
    def _create_list_chunk(self, section: DocumentSection) -> StructuredChunk:
        """Create a chunk for list content - complete unit, no overlap"""
        return StructuredChunk(
            text=section.text,
            chunk_type="list",
            hierarchy_level=section.hierarchy_level,
            page_number=section.page_number,
            section_context="list_content",
            word_count=len(section.text.split()),
            sentence_count=section.text.count('\n') + 1,  # List items
            bounding_box=section.bounding_box,
            metadata={
                'section_type': section.section_type.value,
                'confidence': section.confidence,
                'is_list': True,
                'overlap_strategy': 'none',
                'smart_chunking': True
            }
        )
    
    def _create_header_with_context(self, section: DocumentSection, all_sections: List[DocumentSection], index: int) -> StructuredChunk:
        """Create header chunk with natural context - no artificial overlap"""
        
        # Include header and naturally following content
        context_text = section.text
        included_sections = [section.section_type.value]
        
        # Add following content if it's a paragraph and reasonably sized
        if index + 1 < len(all_sections):
            next_section = all_sections[index + 1]
            if (next_section.section_type == SectionType.PARAGRAPH and 
                len(next_section.text) < self.max_chunk_size // 2):
                context_text += '\n\n' + next_section.text
                included_sections.append('following_paragraph')
        
        return StructuredChunk(
            text=context_text,
            chunk_type="header_with_context",
            hierarchy_level=section.hierarchy_level,
            page_number=section.page_number,
            section_context=f"header_level_{section.hierarchy_level}",
            word_count=len(context_text.split()),
            sentence_count=self._count_sentences(context_text),
            bounding_box=section.bounding_box,
            metadata={
                'section_type': section.section_type.value,
                'confidence': section.confidence,
                'is_header': True,
                'includes_context': True,
                'included_sections': included_sections,
                'overlap_strategy': 'natural_context',
                'smart_chunking': True
            }
        )
    
    def _create_header_chunk(self, section: DocumentSection) -> StructuredChunk:
        """Create simple header chunk without context"""
        return StructuredChunk(
            text=section.text,
            chunk_type="header",
            hierarchy_level=section.hierarchy_level,
            page_number=section.page_number,
            section_context=f"header_level_{section.hierarchy_level}",
            word_count=len(section.text.split()),
            sentence_count=self._count_sentences(section.text),
            bounding_box=section.bounding_box,
            metadata={
                'section_type': section.section_type.value,
                'confidence': section.confidence,
                'is_header': True,
                'overlap_strategy': 'none',
                'smart_chunking': True
            }
        )
