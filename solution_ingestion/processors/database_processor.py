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
        """Skip solution storage - solutions are not stored in RDBMS."""
        logger.info(f"Skipping RDBMS storage for {len(solutions)} solutions (stored in OpenSearch and data lake only)")
        return
    
    def store_chunks(self, chunks: List[Chunk]):
        """Skip chunk storage - chunks are not stored in RDBMS."""
        logger.info(f"Skipping RDBMS storage for {len(chunks)} chunks (stored in OpenSearch and data lake only)")
        return
    
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