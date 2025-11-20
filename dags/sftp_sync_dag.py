"""
SFTP File Synchronization DAG

This DAG synchronizes files from a source SFTP server to a target SFTP server
while preserving the directory structure. It supports:
- Unidirectional sync (source -> target)
- Directory structure preservation
- Incremental file transfer
- Scalable architecture for large files
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import os
import logging

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.providers.sftp.hooks.sftp import SFTPHook
from airflow.exceptions import AirflowException

# Configure logging
logger = logging.getLogger(__name__)

# Default arguments
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 3, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'catchup': False,
}

# DAG configuration
DAG_ID = 'sftp_file_sync'
SCHEDULE_INTERVAL = timedelta(hours=1)  # Run every hour

# SFTP connection configurations (these should be set as Airflow Variables or Connections)
SOURCE_SFTP_CONN_ID = 'sftp_source'
TARGET_SFTP_CONN_ID = 'sftp_target'

# Configuration variables - load defaults, actual values loaded at runtime
BATCH_SIZE = 100
MAX_FILE_SIZE_MB = 1024


class SFTPFileSync:
    """
    A class to handle SFTP file synchronization operations.
    This provides abstraction for potential future data source changes.
    """
    
    def __init__(self, source_conn_id: str, target_conn_id: str):
        self.source_conn_id = source_conn_id
        self.target_conn_id = target_conn_id
    
    def get_source_hook(self) -> SFTPHook:
        """Get SFTP hook for source server."""
        return SFTPHook(ssh_conn_id=self.source_conn_id)
    
    def get_target_hook(self) -> SFTPHook:
        """Get SFTP hook for target server."""
        return SFTPHook(ssh_conn_id=self.target_conn_id)
    
    def list_files_recursive(self, hook: SFTPHook, path: str, sync_root_dir: str) -> List[Dict[str, Any]]:
        """
        Recursively list all files in a directory with metadata.
        
        Args:
            hook: SFTP hook instance
            path: Directory path to scan
            sync_root_dir: Root directory for sync operations
            
        Returns:
            List of file dictionaries with metadata
        """
        files = []
        
        try:
            sftp_client = hook.get_conn()
            items = hook.list_directory(path)
            
            for item in items:
                item_path = os.path.join(path, item).replace('\\', '/')
                
                try:
                    # Get file attributes using stat
                    attrs = sftp_client.stat(item_path)
                    
                    # Check if it's a directory using stat module
                    import stat as stat_module
                    if stat_module.S_ISDIR(attrs.st_mode):
                        # Recursively scan subdirectory
                        files.extend(self.list_files_recursive(hook, item_path, sync_root_dir))
                    else:
                        # It's a file
                        # Calculate relative path from the sync root
                        relative = item_path.replace(sync_root_dir, '').lstrip('/')
                        
                        files.append({
                            'path': item_path,
                            'size': attrs.st_size,
                            'modified_time': attrs.st_mtime,
                            'relative_path': relative
                        })
                        logger.debug(f"Found file: {item_path} -> relative: {relative}")
                        
                except Exception as e:
                    logger.warning(f"Could not get attributes for {item_path}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")
            
        return files
    
    def file_exists_on_target(self, target_hook: SFTPHook, file_path: str) -> bool:
        """Check if file exists on target server."""
        try:
            sftp_client = target_hook.get_conn()
            sftp_client.stat(file_path)
            return True
        except:
            return False
    
    def ensure_target_directory(self, target_hook: SFTPHook, file_path: str):
        """Ensure target directory structure exists."""
        dir_path = os.path.dirname(file_path)
        if dir_path and dir_path != '/' and dir_path != '':
            # Create directory recursively
            parts = dir_path.strip('/').split('/')
            current_path = ''
            sftp_client = target_hook.get_conn()
            
            for part in parts:
                if not part:  # Skip empty parts
                    continue
                    
                if current_path:
                    current_path = f"{current_path}/{part}"
                else:
                    current_path = part
                    
                try:
                    sftp_client.stat(current_path)
                    logger.debug(f"Directory exists: {current_path}")
                except:
                    try:
                        sftp_client.mkdir(current_path)
                        logger.info(f"Created directory: {current_path}")
                    except Exception as e:
                        logger.error(f"Failed to create directory {current_path}: {e}")
                        raise
    
    def sync_file(self, source_hook: SFTPHook, target_hook: SFTPHook, 
                  source_path: str, target_path: str, file_size: int, max_file_size_mb: int = 1024) -> bool:
        """
        Sync a single file from source to target.
        
        Args:
            source_hook: Source SFTP hook
            target_hook: Target SFTP hook
            source_path: Source file path
            target_path: Target file path
            file_size: File size in bytes
            max_file_size_mb: Maximum file size in MB
            
        Returns:
            True if sync successful, False otherwise
        """
        try:
            # Check file size limits
            file_size_mb = file_size / (1024 * 1024)
            if file_size_mb > max_file_size_mb:
                logger.warning(f"File {source_path} ({file_size_mb:.2f}MB) exceeds size limit ({max_file_size_mb}MB)")
                return False
            
            # Ensure target directory exists
            self.ensure_target_directory(target_hook, target_path)
            
            # Use temporary file for atomic transfer
            temp_target_path = f"{target_path}.tmp"
            
            # Download from source and upload to target
            with source_hook.get_conn().open(source_path, 'rb') as source_file:
                with target_hook.get_conn().open(temp_target_path, 'wb') as target_file:
                    # Transfer in chunks for large files
                    chunk_size = 8192
                    total_transferred = 0
                    
                    while True:
                        chunk = source_file.read(chunk_size)
                        if not chunk:
                            break
                        target_file.write(chunk)
                        total_transferred += len(chunk)
            
            # Atomic move from temp to final location
            target_hook.get_conn().rename(temp_target_path, target_path)
            
            logger.info(f"Successfully synced {source_path} -> {target_path} ({file_size_mb:.2f}MB)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync {source_path} -> {target_path}: {e}")
            # Clean up temp file if it exists
            try:
                target_hook.delete_file(temp_target_path)
            except:
                pass
            return False


def discover_source_files(**context) -> List[Dict[str, Any]]:
    """
    Discover all files on the source SFTP server.
    
    Returns:
        List of file metadata dictionaries
    """
    # Load configuration at runtime
    sync_root_dir = Variable.get('SFTP_SYNC_ROOT_DIR', default_var='/upload')
    
    sync_handler = SFTPFileSync(SOURCE_SFTP_CONN_ID, TARGET_SFTP_CONN_ID)
    source_hook = sync_handler.get_source_hook()
    
    logger.info(f"Discovering files in {sync_root_dir}")
    logger.info(f"Using SYNC_ROOT_DIR: '{sync_root_dir}'")
    files = sync_handler.list_files_recursive(source_hook, sync_root_dir, sync_root_dir)
    
    logger.info(f"Discovered {len(files)} files on source server")
    
    # Log sample files for debugging
    if files:
        logger.info(f"Sample file info: {files[0]}")
    
    # Store file list in XCom for next task
    return files


def sync_files(**context) -> Dict[str, int]:
    """
    Sync files from source to target SFTP server.
    
    Returns:
        Dictionary with sync statistics
    """
    # Load configuration at runtime
    sync_root_dir = Variable.get('SFTP_SYNC_ROOT_DIR', default_var='/upload')
    batch_size = int(Variable.get('SFTP_BATCH_SIZE', default_var='100'))
    max_file_size_mb = int(Variable.get('SFTP_MAX_FILE_SIZE_MB', default_var='1024'))
    
    # Get file list from previous task
    files = context['task_instance'].xcom_pull(task_ids='discover_files')
    
    if not files:
        logger.info("No files to sync")
        return {'synced': 0, 'skipped': 0, 'failed': 0}
    
    sync_handler = SFTPFileSync(SOURCE_SFTP_CONN_ID, TARGET_SFTP_CONN_ID)
    source_hook = sync_handler.get_source_hook()
    target_hook = sync_handler.get_target_hook()
    
    stats = {'synced': 0, 'skipped': 0, 'failed': 0}
    
    # Process files in batches to avoid memory issues
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(files)-1)//batch_size + 1}")
        
        for file_info in batch:
            source_path = file_info['path']
            relative_path = file_info['relative_path']
            
            logger.info(f"File info - source: {source_path}, relative: {relative_path}")
            logger.info(f"SYNC_ROOT_DIR value: '{sync_root_dir}'")
            
            # Construct target path maintaining directory structure within upload directory
            # The target path should mirror the source structure
            # Example: source=/upload/backups/file.txt, relative=backups/file.txt
            # Target should be: upload/backups/file.txt (relative to /home/targetuser/)
            target_path = os.path.join(sync_root_dir.lstrip('/'), relative_path).replace('\\', '/')
            
            logger.info(f"Target path after construction: '{target_path}'")
            
            logger.info(f"Syncing: {source_path} -> {target_path}")
            
            # Check if file already exists on target
            if sync_handler.file_exists_on_target(target_hook, target_path):
                logger.debug(f"File already exists on target: {target_path}")
                stats['skipped'] += 1
                continue
            
            # Sync the file
            success = sync_handler.sync_file(
                source_hook, target_hook, 
                source_path, target_path, 
                file_info['size'],
                max_file_size_mb
            )
            
            if success:
                stats['synced'] += 1
            else:
                stats['failed'] += 1
    
    logger.info(f"Sync completed. Stats: {stats}")
    return stats


# Create the DAG
dag = DAG(
    DAG_ID,
    default_args=default_args,
    description='Synchronize files from source SFTP to target SFTP',
    schedule_interval=SCHEDULE_INTERVAL,
    max_active_runs=1,  # Prevent concurrent runs
    tags=['sftp', 'sync', 'file-transfer'],
)

# Task 1: Discover files on source server
discover_task = PythonOperator(
    task_id='discover_files',
    python_callable=discover_source_files,
    dag=dag,
)

# Task 2: Sync files to target server
sync_task = PythonOperator(
    task_id='sync_files',
    python_callable=sync_files,
    dag=dag,
)

# Define task dependencies
discover_task >> sync_task
