"""
SFTP Sync with Transformations - Example DAG

This DAG demonstrates how to extend the basic SFTP sync functionality
with file transformations before loading into the target system.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.providers.sftp.hooks.sftp import SFTPHook

# Import custom plugin utilities
try:
    from plugins.sftp_utilities import (
        SFTPFileTransformOperator,
        compress_file_transformation,
        csv_to_json_transformation,
        SFTPBatchProcessor
    )
except ImportError:
    logging.warning("Custom SFTP utilities plugin not available")


logger = logging.getLogger(__name__)

# Default arguments
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 3, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=3),
    'catchup': False,
}

# DAG configuration
DAG_ID = 'sftp_sync_with_transformations'
SCHEDULE_INTERVAL = timedelta(hours=6)  # Run every 6 hours

# SFTP connection configurations
SOURCE_SFTP_CONN_ID = 'sftp_source'
TARGET_SFTP_CONN_ID = 'sftp_target'


def discover_csv_files(**context) -> List[Dict[str, Any]]:
    """
    Discover CSV files on the source SFTP server for transformation.
    
    Returns:
        List of CSV file metadata dictionaries
    """
    source_hook = SFTPHook(ssh_conn_id=SOURCE_SFTP_CONN_ID)
    
    # Get root directory from variables
    root_dir = Variable.get('SFTP_SYNC_ROOT_DIR', default_var='/upload')
    
    csv_files = []
    
    def scan_directory(path: str):
        """Recursively scan for CSV files."""
        try:
            sftp_client = source_hook.get_conn()
            items = source_hook.list_directory(path)
            
            for item in items:
                item_path = f"{path.rstrip('/')}/{item}"
                
                try:
                    # Get file attributes using stat
                    import stat as stat_module
                    attrs = sftp_client.stat(item_path)
                    
                    if stat_module.S_ISDIR(attrs.st_mode):  # Directory
                        scan_directory(item_path)
                    else:  # File
                        if item.lower().endswith('.csv'):
                            csv_files.append({
                                'path': item_path,
                                'size': attrs.st_size,
                                'name': item
                            })
                        
                except Exception as e:
                    logger.warning(f"Could not check {item_path}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scanning directory {path}: {e}")
    
    scan_directory(root_dir)
    
    logger.info(f"Discovered {len(csv_files)} CSV files for transformation")
    return csv_files


def transform_csv_files(**context) -> Dict[str, int]:
    """
    Transform CSV files to JSON format.
    
    Returns:
        Transformation statistics
    """
    csv_files = context['task_instance'].xcom_pull(task_ids='discover_csv_files')
    
    if not csv_files:
        logger.info("No CSV files to transform")
        return {'transformed': 0, 'failed': 0}
    
    source_hook = SFTPHook(ssh_conn_id=SOURCE_SFTP_CONN_ID)
    target_hook = SFTPHook(ssh_conn_id=TARGET_SFTP_CONN_ID)
    
    stats = {'transformed': 0, 'failed': 0}
    
    for file_info in csv_files:
        csv_file = file_info['path']
        file_name = file_info['name']
        
        try:
            logger.info(f"Transforming CSV to JSON: {csv_file}")
            
            # Download file from source to temp location
            import tempfile
            import os
            
            with tempfile.TemporaryDirectory() as temp_dir:
                local_csv_path = os.path.join(temp_dir, file_name)
                local_json_path = local_csv_path.replace('.csv', '.json')
                
                # Download CSV
                source_hook.retrieve_file(csv_file, local_csv_path)
                
                # Transform CSV to JSON
                try:
                    csv_to_json_transformation(local_csv_path)
                except Exception as e:
                    logger.error(f"Transformation failed for {csv_file}: {e}")
                    stats['failed'] += 1
                    continue
                
                # Upload JSON to target (same path structure, just .json extension)
                target_path = csv_file.replace('.csv', '.json')
                target_hook.store_file(target_path, local_json_path)
                
                logger.info(f"Successfully transformed {csv_file} -> {target_path}")
                stats['transformed'] += 1
                
        except Exception as e:
            logger.error(f"Failed to transform {csv_file}: {e}")
            stats['failed'] += 1
    
    logger.info(f"CSV transformation completed. Stats: {stats}")
    return stats


def compress_large_files(**context) -> Dict[str, int]:
    """
    Compress files larger than a specified threshold.
    
    Returns:
        Compression statistics
    """
    import os
    import stat as stat_module
    
    # Size threshold in MB
    size_threshold_mb = float(Variable.get('COMPRESSION_THRESHOLD_MB', default_var='10'))
    size_threshold_bytes = size_threshold_mb * 1024 * 1024
    
    # Get root directory from variables
    sync_root_dir = Variable.get('SFTP_SYNC_ROOT_DIR', default_var='/upload')
    
    source_hook = SFTPHook(ssh_conn_id=SOURCE_SFTP_CONN_ID)
    target_hook = SFTPHook(ssh_conn_id=TARGET_SFTP_CONN_ID)
    
    # Recursively find all files
    def list_files_recursive(path: str) -> List[Dict[str, Any]]:
        """Recursively list all files with metadata."""
        files = []
        try:
            sftp_client = source_hook.get_conn()
            items = source_hook.list_directory(path)
            
            for item in items:
                item_path = os.path.join(path, item).replace('\\', '/')
                
                try:
                    attrs = sftp_client.stat(item_path)
                    
                    if stat_module.S_ISDIR(attrs.st_mode):
                        files.extend(list_files_recursive(item_path))
                    else:
                        relative = item_path.replace(sync_root_dir, '').lstrip('/')
                        files.append({
                            'path': item_path,
                            'size': attrs.st_size,
                            'relative_path': relative
                        })
                except Exception as e:
                    logger.warning(f"Could not get attributes for {item_path}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")
        
        return files
    
    all_files = list_files_recursive(sync_root_dir)
    
    # Filter large files
    large_files = [f for f in all_files if f['size'] > size_threshold_bytes]
    
    logger.info(f"Found {len(large_files)} files larger than {size_threshold_mb}MB")
    
    stats = {'compressed': 0, 'failed': 0, 'skipped': 0}
    
    for file_info in large_files:
        source_path = file_info['path']
        
        try:
            # Skip already compressed files
            if source_path.endswith('.gz'):
                logger.info(f"Skipping already compressed file: {source_path}")
                stats['skipped'] += 1
                continue
            
            logger.info(f"Compressing large file: {source_path} ({file_info['size'] / (1024*1024):.2f}MB)")
            
            # Download, compress, and upload
            import tempfile
            
            with tempfile.TemporaryDirectory() as temp_dir:
                file_name = os.path.basename(source_path)
                local_path = os.path.join(temp_dir, file_name)
                
                # Download file
                source_hook.retrieve_file(source_path, local_path)
                
                # Compress it
                compressed_path = compress_file_transformation(local_path)
                
                # Upload compressed version to target
                # Construct target path with .gz extension
                target_path = os.path.join(sync_root_dir.lstrip('/'), file_info['relative_path']).replace('\\', '/')
                target_path_gz = f"{target_path}.gz"
                
                target_hook.store_file(target_path_gz, compressed_path)
                
                logger.info(f"Successfully compressed {source_path} -> {target_path_gz}")
                stats['compressed'] += 1
                
        except Exception as e:
            logger.error(f"Failed to compress {source_path}: {e}")
            stats['failed'] += 1
    
    logger.info(f"File compression completed. Stats: {stats}")
    return stats


def health_check_connections(**context) -> Dict[str, Any]:
    """
    Perform health checks on SFTP connections.
    
    Returns:
        Health check results
    """
    results = {
        'source': {'status': 'unknown', 'connection_id': SOURCE_SFTP_CONN_ID},
        'target': {'status': 'unknown', 'connection_id': TARGET_SFTP_CONN_ID},
        'overall_status': 'unknown'
    }
    
    # Check source connection
    try:
        source_hook = SFTPHook(ssh_conn_id=SOURCE_SFTP_CONN_ID)
        source_hook.list_directory('/')
        results['source'] = {
            'status': 'healthy',
            'connection_id': SOURCE_SFTP_CONN_ID,
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Source connection {SOURCE_SFTP_CONN_ID} is healthy")
    except Exception as e:
        results['source'] = {
            'status': 'unhealthy',
            'connection_id': SOURCE_SFTP_CONN_ID,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        logger.error(f"Source connection {SOURCE_SFTP_CONN_ID} is unhealthy: {e}")
    
    # Check target connection
    try:
        target_hook = SFTPHook(ssh_conn_id=TARGET_SFTP_CONN_ID)
        target_hook.list_directory('/')
        results['target'] = {
            'status': 'healthy',
            'connection_id': TARGET_SFTP_CONN_ID,
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Target connection {TARGET_SFTP_CONN_ID} is healthy")
    except Exception as e:
        results['target'] = {
            'status': 'unhealthy',
            'connection_id': TARGET_SFTP_CONN_ID,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        logger.error(f"Target connection {TARGET_SFTP_CONN_ID} is unhealthy: {e}")
    
    # Determine overall status
    results['overall_status'] = 'healthy' if (
        results['source']['status'] == 'healthy' and 
        results['target']['status'] == 'healthy'
    ) else 'unhealthy'
    
    logger.info(f"Health check results: {results}")
    
    # Raise exception if any connection is unhealthy
    if results['overall_status'] == 'unhealthy':
        raise Exception(f"SFTP health check failed: {results}")
    
    return results


# Create the DAG
dag = DAG(
    DAG_ID,
    default_args=default_args,
    description='SFTP sync with file transformations and health checks',
    schedule_interval=SCHEDULE_INTERVAL,
    max_active_runs=1,
    tags=['sftp', 'sync', 'transformation', 'etl'],
)

# Task 1: Health check before processing
health_check_task = PythonOperator(
    task_id='health_check',
    python_callable=health_check_connections,
    dag=dag,
)

# Task 2: Discover CSV files for transformation
discover_csv_task = PythonOperator(
    task_id='discover_csv_files',
    python_callable=discover_csv_files,
    dag=dag,
)

# Task 3: Transform CSV files to JSON
transform_csv_task = PythonOperator(
    task_id='transform_csv_files',
    python_callable=transform_csv_files,
    dag=dag,
)

# Task 4: Compress large files
compress_task = PythonOperator(
    task_id='compress_large_files',
    python_callable=compress_large_files,
    dag=dag,
)

# Define task dependencies
# First check health, then run discovery and compression in parallel
# Finally transform the CSV files
health_check_task >> [discover_csv_task, compress_task]
discover_csv_task >> transform_csv_task
