"""
SFTP Utilities Plugin

This plugin provides additional utilities for SFTP operations,
including enhanced error handling, monitoring, and extensibility features.
"""

from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from airflow.plugins_manager import AirflowPlugin
from airflow.providers.sftp.hooks.sftp import SFTPHook
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults


logger = logging.getLogger(__name__)


class SFTPSyncMonitor:
    """Monitor and track SFTP synchronization operations."""
    
    @staticmethod
    def log_sync_metrics(stats: Dict[str, int], execution_date: datetime):
        """Log synchronization metrics for monitoring."""
        logger.info(f"SFTP Sync Metrics for {execution_date}:")
        logger.info(f"  Files Synced: {stats.get('synced', 0)}")
        logger.info(f"  Files Skipped: {stats.get('skipped', 0)}")
        logger.info(f"  Files Failed: {stats.get('failed', 0)}")
        
        total_files = sum(stats.values())
        if total_files > 0:
            success_rate = (stats.get('synced', 0) / total_files) * 100
            logger.info(f"  Success Rate: {success_rate:.2f}%")


class SFTPFileTransformOperator(BaseOperator):
    """
    Extended SFTP operator that supports file transformations.
    
    This operator demonstrates extensibility for adding transformations
    before loading files into the target system.
    """
    
    @apply_defaults
    def __init__(
        self,
        source_conn_id: str,
        target_conn_id: str,
        file_path: str,
        transformation_function: Optional[callable] = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.source_conn_id = source_conn_id
        self.target_conn_id = target_conn_id
        self.file_path = file_path
        self.transformation_function = transformation_function
    
    def execute(self, context):
        """Execute the file transformation and transfer."""
        source_hook = SFTPHook(ssh_conn_id=self.source_conn_id)
        target_hook = SFTPHook(ssh_conn_id=self.target_conn_id)
        
        # Download file from source
        local_temp_path = f"/tmp/{self.file_path.split('/')[-1]}"
        source_hook.retrieve_file(self.file_path, local_temp_path)
        
        # Apply transformation if provided
        if self.transformation_function:
            try:
                transformed_path = self.transformation_function(local_temp_path)
                local_temp_path = transformed_path
                logger.info(f"Applied transformation to {self.file_path}")
            except Exception as e:
                logger.error(f"Transformation failed for {self.file_path}: {e}")
                raise
        
        # Upload to target
        target_hook.store_file(self.file_path, local_temp_path)
        
        # Clean up local temp file
        import os
        if os.path.exists(local_temp_path):
            os.remove(local_temp_path)
        
        logger.info(f"Successfully processed {self.file_path}")


class SFTPHealthChecker:
    """Health checker for SFTP connections."""
    
    @staticmethod
    def check_connection(conn_id: str) -> Dict[str, Any]:
        """
        Check SFTP connection health.
        
        Args:
            conn_id: Airflow connection ID
            
        Returns:
            Dictionary with health check results
        """
        try:
            hook = SFTPHook(ssh_conn_id=conn_id)
            
            # Try to list root directory
            files = hook.list_directory('/')
            
            return {
                'status': 'healthy',
                'connection_id': conn_id,
                'timestamp': datetime.now().isoformat(),
                'root_files_count': len(files) if files else 0
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'connection_id': conn_id,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


class SFTPBatchProcessor:
    """Batch processor for handling large numbers of files efficiently."""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
    
    def process_files_in_batches(
        self, 
        files: List[Dict[str, Any]], 
        processor_function: callable
    ) -> Dict[str, int]:
        """
        Process files in batches to handle scale efficiently.
        
        Args:
            files: List of file metadata dictionaries
            processor_function: Function to process each batch
            
        Returns:
            Processing statistics
        """
        stats = {'processed': 0, 'failed': 0, 'total_batches': 0}
        
        total_batches = (len(files) - 1) // self.batch_size + 1
        stats['total_batches'] = total_batches
        
        for i in range(0, len(files), self.batch_size):
            batch = files[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} files)")
            
            try:
                batch_result = processor_function(batch)
                stats['processed'] += batch_result.get('processed', 0)
                stats['failed'] += batch_result.get('failed', 0)
                
            except Exception as e:
                logger.error(f"Batch {batch_num} failed: {e}")
                stats['failed'] += len(batch)
        
        return stats


# Example transformation functions
def compress_file_transformation(file_path: str) -> str:
    """
    Example transformation: compress a file.
    
    Args:
        file_path: Path to the file to compress
        
    Returns:
        Path to the compressed file
    """
    import gzip
    import shutil
    
    compressed_path = f"{file_path}.gz"
    
    with open(file_path, 'rb') as f_in:
        with gzip.open(compressed_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    return compressed_path


def csv_to_json_transformation(file_path: str) -> str:
    """
    Example transformation: convert CSV to JSON.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        Path to the JSON file
    """
    import pandas as pd
    import json
    
    if not file_path.lower().endswith('.csv'):
        return file_path  # Return original if not CSV
    
    json_path = file_path.replace('.csv', '.json')
    
    # Read CSV and convert to JSON
    df = pd.read_csv(file_path)
    df.to_json(json_path, orient='records', indent=2)
    
    return json_path


# Plugin definition
class SFTPUtilitiesPlugin(AirflowPlugin):
    name = "sftp_utilities"
    operators = [SFTPFileTransformOperator]
    hooks = []
    executors = []
    macros = []
    admin_views = []
    flask_blueprints = []
    menu_links = []
