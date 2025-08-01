#!/usr/bin/env python3
"""
Bulk Load Monitor - Core Logic
Monitors Neptune bulk loads and updates database status when complete
"""

import logging
import boto3
from datetime import datetime
from typing import Dict, List, Any

# Import from standardized layers
from utils.DatabaseManager import DatabaseManager
from utils.KnowledgeGraphManager import KnowledgeGraphManager

logger = logging.getLogger(__name__)

class BulkLoadMonitor:
    """Monitor Neptune bulk loads and update processing status"""
    
    def __init__(self):
        """Initialize monitor with database and KG managers"""
        try:
            self.db_manager = DatabaseManager()
            self.kg_manager = KnowledgeGraphManager()
            self.sns_client = boto3.client('sns')
            logger.info("Bulk load monitor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize bulk load monitor: {e}")
            raise
    
    def monitor_active_loads(self) -> Dict[str, Any]:
        """
        Monitor all active bulk loads and update status when complete
        
        Returns:
            Dictionary with monitoring results
        """
        try:
            # Get active bulk loads from database (no SQL in Lambda)
            active_loads = self.db_manager.get_active_bulk_loads()
            
            results = {
                'total_active_loads': len(active_loads),
                'completed': 0,
                'failed': 0,
                'still_in_progress': 0,
                'errors': []
            }
            
            logger.info(f"Found {len(active_loads)} active bulk loads to monitor")
            
            for load_info in active_loads:
                try:
                    result = self._monitor_single_load(load_info)
                    results[result['status']] += 1
                    
                except Exception as e:
                    logger.error(f"Error monitoring load {load_info.get('load_id', 'unknown')}: {e}")
                    results['errors'].append({
                        'load_id': load_info.get('load_id', 'unknown'),
                        'doc_id': load_info.get('doc_id', 'unknown'),
                        'error': str(e)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in monitor_active_loads: {e}")
            raise
    
    def _monitor_single_load(self, load_info: Dict[str, Any]) -> Dict[str, str]:
        """
        Monitor a single bulk load
        
        Args:
            load_info: Dict with doc_id, load_id, started_at, metadata
            
        Returns:
            Dict with status: 'completed', 'failed', or 'still_in_progress'
        """
        doc_id = load_info['doc_id']
        load_id = load_info['load_id']
        
        logger.info(f"Checking bulk load status: {load_id} for document {doc_id}")
        
        try:
            # Check Neptune status using KG manager
            status_info = self.kg_manager.get_bulk_load_status(load_id)
            neptune_status = status_info.get('status', 'UNKNOWN')
            
            logger.info(f"Neptune status for load {load_id}: {neptune_status}")
            
            if neptune_status == 'LOAD_COMPLETED':
                self._handle_completion(doc_id, load_id, status_info)
                return {'status': 'completed'}
                
            elif neptune_status in ['LOAD_FAILED', 'LOAD_CANCELLED']:
                self._handle_failure(doc_id, load_id, status_info)
                return {'status': 'failed'}
                
            else:
                # Still in progress (LOAD_IN_PROGRESS, LOAD_WAITING, etc.)
                logger.info(f"Load {load_id} still in progress with status: {neptune_status}")
                return {'status': 'still_in_progress'}
                
        except Exception as e:
            logger.error(f"Error checking status for load {load_id}: {e}")
            raise
    
    def _handle_completion(self, doc_id: str, load_id: str, status_info: Dict[str, Any]):
        """Handle successful bulk load completion"""
        try:
            logger.info(f"Bulk load {load_id} completed successfully for document {doc_id}")
            
            # Update database status using existing method
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='kg_triples_load',
                status='completed',
                system_id=load_id,
                metadata={
                    'bulk_load_completed': datetime.utcnow().isoformat() + 'Z',
                    'records_loaded': status_info.get('totalRecords', 0),
                    'load_duration_ms': status_info.get('timeElapsed', 0),
                    'completion_method': 'bulk_load_monitor'
                }
            )
            
            logger.info(f"Updated database status to completed for document {doc_id}")
            
        except Exception as e:
            logger.error(f"Error handling completion for load {load_id}: {e}")
            raise
    
    def _handle_failure(self, doc_id: str, load_id: str, status_info: Dict[str, Any]):
        """Handle bulk load failure"""
        try:
            error_message = status_info.get('errorMessage', 'Unknown bulk load error')
            logger.error(f"Bulk load {load_id} failed for document {doc_id}: {error_message}")
            
            # Update database status using existing method
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='kg_triples_load',
                status='failed',
                system_id=load_id,
                error_message=f"Bulk load failed: {error_message}",
                metadata={
                    'bulk_load_failed': datetime.utcnow().isoformat() + 'Z',
                    'failure_reason': error_message,
                    'completion_method': 'bulk_load_monitor'
                }
            )
            
            logger.info(f"Updated database status to failed for document {doc_id}")
            
        except Exception as e:
            logger.error(f"Error handling failure for load {load_id}: {e}")
            raise
