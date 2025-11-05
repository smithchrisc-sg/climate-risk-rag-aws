#!/usr/bin/env python3
"""
Database Processor for Solution Ingestion
Handles PostgreSQL operations using production DatabaseManager.
"""

import logging
import sys
import os
from typing import List
from pathlib import Path

from database_core_layer.utils.DatabaseManager import DatabaseManager
from models.solution import Solution
from generators.chunk_generator import Chunk

logger = logging.getLogger(__name__)

class DatabaseProcessor:
    """Handles database operations for solution ingestion."""
    
    def __init__(self, env):
        self.env = env
        self.db_manager = None
        self._init_database()
    
    def _init_database(self):
        """Initialize database connection."""
        try:
            self.db_manager = DatabaseManager()
            logger.info("Database connection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def store_solutions(self, solutions: List[Solution]):
        """Store solutions in PostgreSQL."""
        logger.info(f"Storing {len(solutions)} solutions in database")
        
        stored_count = 0
        for solution in solutions:
            try:
                # Store document metadata
                self.db_manager.store_document_metadata(
                    doc_id=solution.doc_id,
                    title=solution.name,
                    source_url=solution.source_url,
                    metadata=solution.get_metadata()
                )
                
                # Store full text
                if hasattr(solution, 'pseudo_document_text') and solution.pseudo_document_text:
                    text_content = solution.pseudo_document_text
                else:
                    text_content = solution.get_full_text()
                
                self.db_manager.store_document_text(
                    doc_id=solution.doc_id,
                    text_content=text_content
                )
                
                # Update processing status
                self.db_manager.update_processing_status(
                    doc_id=solution.doc_id,
                    stage='solution_ingestion',
                    status='completed'
                )
                
                stored_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to store solution {solution.id}: {e}")
                continue
        
        logger.info(f"Successfully stored {stored_count}/{len(solutions)} solutions")
    
    def store_chunks(self, chunks: List[Chunk]):
        """Store chunks in PostgreSQL."""
        logger.info(f"Storing {len(chunks)} chunks in database")
        
        stored_count = 0
        for chunk in chunks:
            try:
                # Store chunk data
                self.db_manager.store_chunk_data(
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    chunk_index=self._get_chunk_index(chunk.chunk_type),
                    text_content=chunk.text,
                    metadata=chunk.metadata
                )
                
                stored_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to store chunk {chunk.chunk_id}: {e}")
                continue
        
        logger.info(f"Successfully stored {stored_count}/{len(chunks)} chunks")
    
    def _get_chunk_index(self, chunk_type: str) -> int:
        """Get numeric index for chunk type."""
        type_mapping = {
            'desc': 1,
            'highlights': 2,
            'results': 3
        }
        return type_mapping.get(chunk_type, 1)
    
    def check_existing_solutions(self, solutions: List[Solution]) -> List[Solution]:
        """Filter out solutions that already exist in database."""
        new_solutions = []
        
        for solution in solutions:
            try:
                existing = self.db_manager.get_document_by_url(solution.source_url)
                if existing:
                    logger.debug(f"Solution already exists: {solution.source_url}")
                else:
                    new_solutions.append(solution)
            except Exception as e:
                logger.warning(f"Error checking existing solution {solution.id}: {e}")
                # Include in new_solutions if we can't check
                new_solutions.append(solution)
        
        logger.info(f"Found {len(new_solutions)} new solutions out of {len(solutions)} total")
        return new_solutions
    
    def get_solution_stats(self) -> dict:
        """Get statistics about stored solutions."""
        try:
            # Get document count
            doc_count = self.db_manager.get_document_count()
            
            # Get chunk count
            chunk_count = self.db_manager.get_chunk_count()
            
            return {
                'documents': doc_count,
                'chunks': chunk_count
            }
        except Exception as e:
            logger.error(f"Failed to get solution stats: {e}")
            return {'documents': 0, 'chunks': 0}