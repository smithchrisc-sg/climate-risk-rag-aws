#!/usr/bin/env python3
"""
Bulk Load Manager - Neptune bulk load operations from S3
Handles efficient loading of large RDF datasets into Neptune
"""
import logging
import time
import json
from typing import Dict, List, Any, Optional
import requests
from .kg_exceptions import KGInsertError, KGValidationError, KGTimeoutError

class BulkLoadManager:
    """Manages Neptune bulk load operations from S3"""
    
    # Load status constants
    LOAD_NOT_STARTED = "LOAD_NOT_STARTED"
    LOAD_IN_PROGRESS = "LOAD_IN_PROGRESS"
    LOAD_COMPLETED = "LOAD_COMPLETED"
    LOAD_CANCELLED_BY_USER = "LOAD_CANCELLED_BY_USER"
    LOAD_FAILED = "LOAD_FAILED"
    
    # Bulk load threshold (number of estimated triples)
    BULK_LOAD_THRESHOLD = 5000
    
    def __init__(self, kg_manager):
        """
        Initialize bulk load manager
        
        Args:
            kg_manager: KnowledgeGraphManager instance
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.kg_manager = kg_manager
        
        # Neptune loader endpoint
        self.loader_endpoint = f"https://{kg_manager.neptune_endpoint}:{kg_manager.neptune_port}/loader"
        
        # Configuration
        self.default_parallelism = "AUTO"  # AUTO, RESUME, NEW
        self.default_timeout = 3600  # 1 hour default timeout
        self.poll_interval = 10  # Poll every 10 seconds
        
        self.logger.debug(f"BulkLoadManager initialized with endpoint: {self.loader_endpoint}")
    
    def initiate_bulk_load(self, 
                          s3_source_uri: str, 
                          format: str = 'turtle',
                          graph_uri: Optional[str] = None,
                          parallelism: str = None,
                          fail_on_error: bool = False,
                          iam_role_arn: Optional[str] = None) -> str:
        """
        Initiate Neptune bulk load from S3
        
        Args:
            s3_source_uri: S3 URI of the data file (s3://bucket/path/file.ttl)
            format: Data format ('turtle', 'ntriples', 'rdfxml', 'nquads')
            graph_uri: Optional named graph URI
            parallelism: Load parallelism (LOW, MEDIUM, HIGH, OVERSUBSCRIBE)
            fail_on_error: Whether to fail entire load on any error
            iam_role_arn: IAM role ARN for S3 access (auto-detected if not provided)
            
        Returns:
            Load ID for monitoring
        """
        try:
            if not s3_source_uri or not s3_source_uri.startswith('s3://'):
                raise KGValidationError(f"Invalid S3 URI: {s3_source_uri}")
            
            # Use Neptune service role if no IAM role provided
            if not iam_role_arn:
                iam_role_arn = f"arn:aws:iam::{self.kg_manager.account_id}:role/NeptuneLoadFromS3Role"
            
            # Build load request
            load_request = {
                "source": s3_source_uri,
                "format": format.lower(),  # must be one of: rdfxml, turtle, ntriples, nquads, csv
                "region": self.kg_manager.aws_region,
                "failOnError": "FALSE" if not fail_on_error else "TRUE",
                "parallelism": parallelism or self.default_parallelism,  # AUTO, RESUME, NEW
                "updateSingleCardinalityProperties": "FALSE",
                "queueRequest": "TRUE",
                "iamRoleArn": iam_role_arn
            }
            
            # Add named graph if specified
            if graph_uri:
                load_request["namedGraphUri"] = graph_uri
            
            self.logger.info(f"Initiating bulk load from {s3_source_uri}")
            self.logger.debug(f"Load request: {json.dumps(load_request, indent=2)}")
            
            # Send load request
            response = requests.post(
                self.loader_endpoint,
                json=load_request,
                headers={'Content-Type': 'application/json'},
                auth=self.kg_manager.auth,
                timeout=180  # Increased from 30s to 180s for bulk load initiation
            )
            
            response.raise_for_status()
            result = response.json()
            
            load_id = result.get('payload', {}).get('loadId')
            if not load_id:
                raise KGInsertError(f"No load ID returned from Neptune: {result}")
            
            self.logger.info(f"Bulk load initiated successfully. Load ID: {load_id}")
            return load_id
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to initiate bulk load: {e}")
            raise KGInsertError(f"Bulk load initiation failed: {e}")
        except Exception as e:
            self.logger.error(f"Error initiating bulk load: {e}")
            raise KGInsertError(f"Bulk load initiation error: {e}")
    
    def get_load_status(self, load_id: str) -> Dict[str, Any]:
        """
        Get status of a bulk load operation
        
        Args:
            load_id: Load ID from initiate_bulk_load
            
        Returns:
            Dictionary with load status information
        """
        try:
            if not load_id:
                raise KGValidationError("Load ID cannot be empty")
            
            # Get load status
            status_url = f"{self.loader_endpoint}/{load_id}"
            response = requests.get(
                status_url,
                auth=self.kg_manager.auth,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            payload = result.get('payload', {})
            
            # Extract key status information
            status_info = {
                'load_id': load_id,
                'status': payload.get('overallStatus', {}).get('status', 'UNKNOWN'),
                'start_time': payload.get('overallStatus', {}).get('startTime'),
                'time_elapsed': payload.get('overallStatus', {}).get('timeElapsedSeconds'),
                'total_records': payload.get('overallStatus', {}).get('totalRecords', 0),
                'total_duplicates': payload.get('overallStatus', {}).get('totalDuplicates', 0),
                'parsing_errors': payload.get('overallStatus', {}).get('parsingErrors', 0),
                'data_problems': payload.get('overallStatus', {}).get('datatypeErrors', 0),
                'errors': payload.get('overallStatus', {}).get('errors', []),
                'full_payload': payload  # Include full payload for detailed analysis
            }
            
            self.logger.debug(f"Load {load_id} status: {status_info['status']}")
            return status_info
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get load status for {load_id}: {e}")
            raise KGInsertError(f"Load status check failed: {e}")
        except Exception as e:
            self.logger.error(f"Error getting load status for {load_id}: {e}")
            raise KGInsertError(f"Load status error: {e}")
    
    def wait_for_completion(self, 
                           load_id: str, 
                           timeout: int = None,
                           poll_interval: int = None) -> Dict[str, Any]:
        """
        Wait for bulk load to complete
        
        Args:
            load_id: Load ID to monitor
            timeout: Maximum time to wait in seconds
            poll_interval: How often to check status in seconds
            
        Returns:
            Final load status information
        """
        timeout = timeout or self.default_timeout
        poll_interval = poll_interval or self.poll_interval
        
        start_time = time.time()
        self.logger.info(f"Waiting for load {load_id} to complete (timeout: {timeout}s)")
        
        while True:
            try:
                status_info = self.get_load_status(load_id)
                current_status = status_info['status']
                
                # Check for completion states
                if current_status == self.LOAD_COMPLETED:
                    elapsed = time.time() - start_time
                    self.logger.info(f"Load {load_id} completed successfully in {elapsed:.1f}s")
                    self.logger.info(f"Loaded {status_info['total_records']} records")
                    return status_info
                
                elif current_status in [self.LOAD_FAILED, self.LOAD_CANCELLED_BY_USER]:
                    self.logger.error(f"Load {load_id} failed with status: {current_status}")
                    errors = status_info.get('errors', [])
                    if errors:
                        self.logger.error(f"Load errors: {errors}")
                    raise KGInsertError(f"Bulk load failed: {current_status}")
                
                # Check timeout
                if time.time() - start_time > timeout:
                    self.logger.error(f"Load {load_id} timed out after {timeout}s")
                    raise KGTimeoutError(f"Bulk load timed out after {timeout} seconds")
                
                # Log progress
                elapsed = time.time() - start_time
                records = status_info.get('total_records', 0)
                self.logger.debug(f"Load {load_id} in progress: {records} records loaded in {elapsed:.1f}s")
                
                # Wait before next poll
                time.sleep(poll_interval)
                
            except (KGInsertError, KGTimeoutError):
                raise  # Re-raise our exceptions
            except Exception as e:
                self.logger.error(f"Error monitoring load {load_id}: {e}")
                raise KGInsertError(f"Load monitoring error: {e}")
    
    def cancel_load(self, load_id: str) -> bool:
        """
        Cancel a running bulk load operation
        
        Args:
            load_id: Load ID to cancel
            
        Returns:
            True if cancellation successful
        """
        try:
            if not load_id:
                raise KGValidationError("Load ID cannot be empty")
            
            cancel_url = f"{self.loader_endpoint}/{load_id}"
            response = requests.delete(
                cancel_url,
                auth=self.kg_manager.auth,
                timeout=30
            )
            
            response.raise_for_status()
            
            self.logger.info(f"Load {load_id} cancellation requested")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to cancel load {load_id}: {e}")
            raise KGInsertError(f"Load cancellation failed: {e}")
        except Exception as e:
            self.logger.error(f"Error cancelling load {load_id}: {e}")
            raise KGInsertError(f"Load cancellation error: {e}")
    
    def list_recent_loads(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent bulk load operations
        
        Args:
            limit: Maximum number of loads to return
            
        Returns:
            List of load information dictionaries
        """
        try:
            # Get list of recent loads
            response = requests.get(
                self.loader_endpoint,
                params={'limit': limit},
                auth=self.kg_manager.auth,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            loads = result.get('payload', {}).get('loadIds', [])
            
            # Get detailed status for each load
            load_details = []
            for load_info in loads:
                load_id = load_info.get('loadId')
                if load_id:
                    try:
                        status = self.get_load_status(load_id)
                        load_details.append(status)
                    except Exception as e:
                        self.logger.warning(f"Failed to get status for load {load_id}: {e}")
            
            self.logger.debug(f"Retrieved {len(load_details)} recent loads")
            return load_details
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to list recent loads: {e}")
            raise KGInsertError(f"Load listing failed: {e}")
        except Exception as e:
            self.logger.error(f"Error listing recent loads: {e}")
            raise KGInsertError(f"Load listing error: {e}")
    
    def estimate_triple_count(self, ttl_content: str) -> int:
        """
        Estimate number of triples in TTL content
        
        Args:
            ttl_content: TTL content string
            
        Returns:
            Estimated number of triples
        """
        if not ttl_content:
            return 0
        
        # Simple heuristic: count lines that end with '.' and aren't comments/prefixes
        lines = ttl_content.split('\n')
        triple_count = 0
        
        for line in lines:
            line = line.strip()
            if (line.endswith('.') and 
                not line.startswith('@') and 
                not line.startswith('#') and 
                not line.startswith('PREFIX')):
                triple_count += 1
        
        return triple_count
    
    def should_use_bulk_load(self, ttl_content: str) -> bool:
        """
        Determine if bulk load should be used based on content size
        
        Args:
            ttl_content: TTL content to analyze
            
        Returns:
            True if bulk load is recommended
        """
        triple_count = self.estimate_triple_count(ttl_content)
        return triple_count >= self.BULK_LOAD_THRESHOLD
    
    def get_load_statistics(self, load_id: str) -> Dict[str, Any]:
        """
        Get detailed statistics for a completed load
        
        Args:
            load_id: Load ID to get statistics for
            
        Returns:
            Dictionary with detailed load statistics
        """
        status_info = self.get_load_status(load_id)
        
        if status_info['status'] != self.LOAD_COMPLETED:
            self.logger.warning(f"Load {load_id} is not completed, statistics may be incomplete")
        
        # Extract detailed statistics
        payload = status_info.get('full_payload', {})
        
        statistics = {
            'load_id': load_id,
            'status': status_info['status'],
            'total_records': status_info['total_records'],
            'total_duplicates': status_info['total_duplicates'],
            'parsing_errors': status_info['parsing_errors'],
            'data_problems': status_info['data_problems'],
            'time_elapsed': status_info['time_elapsed'],
            'records_per_second': 0,
            'error_details': status_info.get('errors', [])
        }
        
        # Calculate throughput
        if status_info['time_elapsed'] and status_info['total_records']:
            statistics['records_per_second'] = status_info['total_records'] / status_info['time_elapsed']
        
        return statistics
