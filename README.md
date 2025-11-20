# SFTP File Synchronization with Apache Airflow

This project demonstrates Apache Airflow DAGs that synchronize files between SFTP servers with complete directory structure preservation.

## 🚀 Quick Demo Start

**One command to run the complete demo:**

```bash
make start
```

This will:
- Start Airflow (webserver, scheduler, worker) with PostgreSQL and Redis
- Launch source and target SFTP servers with demo data
- Auto-configure Airflow connections
- Display access information

**Demo Access:**
- **Airflow UI**: http://localhost:8080 (username: `airflow`, password: `airflow`)
- **Source SFTP**: localhost:2222 (username: `sourceuser`, password: `sourcepass`)  
- **Target SFTP**: localhost:2223 (username: `targetuser`, password: `targetpass`)

## 📋 What's Included

**Demo Data** (automatically created in source SFTP):
- `demo/customers.csv` - Customer data
- `demo/orders.csv` - Order data  
- `demo/metadata.json` - Metadata file

**Available DAGs:**
1. `sftp_file_sync` - Basic file synchronization
2. `sftp_sync_with_transformations` - Sync with data transformations

## 🎯 How to Demonstrate

1. **Start the demo**: `make start`
2. **Open Airflow UI**: http://localhost:8080
3. **Enable a DAG**: Toggle the DAG on in the UI
4. **Trigger manually**: Click the play button to run immediately
5. **Monitor progress**: Watch the task execution in real-time
6. **Verify results**: Check target SFTP server for transferred files

## Architecture

**Components:**
- **Apache Airflow** (Celery Executor + PostgreSQL + Redis)
- **Source SFTP Server** (port 2222) - Contains demo data
- **Target SFTP Server** (port 2223) - Receives synchronized files

**Features:**
- ✅ **Complete Demo Environment** - Everything runs with one command
- ✅ **Real SFTP Transfer** - Actual file synchronization between servers
- ✅ **Directory Structure Preservation** - Maintains folder hierarchy
- ✅ **Incremental Sync** - Only new/changed files transfer
- ✅ **Error Handling** - Robust retry mechanisms
- ✅ **Monitoring** - Real-time progress tracking in Airflow UI

## 🛠 Available Commands

```bash
make start      # Start complete demo environment
make stop       # Stop all services  
make restart    # Restart services
make logs       # View service logs
make health     # Check service status
make clean      # Clean up everything
make config     # Reconfigure Airflow connections
```

## Quick Start for Development
_AIRFLOW_WWW_USER_PASSWORD=airflow
AIRFLOW_PROJ_DIR=.
EOF
```

### 3. Start the Services

```bash
# Initialize Airflow database and create admin user
docker-compose up airflow-init

# Start all services
docker-compose up -d
```

### 4. Access Airflow Web UI

- URL: http://localhost:8080
- Username: `airflow`
- Password: `airflow`

### 5. Configure SFTP Connections

In the Airflow Web UI, go to **Admin > Connections** and create:

#### Source SFTP Connection
- **Connection Id**: `sftp_source`
- **Connection Type**: `SSH`
- **Host**: `your-source-sftp-host`
- **Username**: `your-username`
- **Password**: `your-password` (or use SSH key)
- **Port**: `22`

#### Target SFTP Connection
- **Connection Id**: `sftp_target`
- **Connection Type**: `SSH`
- **Host**: `your-target-sftp-host`
- **Username**: `your-username`
- **Password**: `your-password` (or use SSH key)
- **Port**: `22`

### 6. Configure Variables

Go to **Admin > Variables** and set:

- `SFTP_SYNC_ROOT_DIR`: Root directory to sync (default: `/`)
- `SFTP_BATCH_SIZE`: Number of files to process per batch (default: `100`)
- `SFTP_MAX_FILE_SIZE_MB`: Maximum file size in MB (default: `1024`)

### 7. Enable and Run the DAG

1. Go to **DAGs** in the Web UI
2. Find `sftp_file_sync` DAG
3. Toggle it ON
4. Trigger manually or wait for scheduled run

## Project Structure

```
cake-tha/
├── docker-compose.yml          # Docker Compose configuration
├── dags/
│   └── sftp_sync_dag.py       # Main synchronization DAG
├── plugins/
│   └── sftp_utilities.py      # Custom utilities and operators
├── logs/                      # Airflow logs (created automatically)
├── config/                    # Airflow configuration (optional)
├── Problem.md                 # Original requirements
└── README.md                  # This file
```

## Configuration Options

### DAG Configuration

The DAG can be customized through Airflow Variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SFTP_SYNC_ROOT_DIR` | `/` | Root directory to synchronize |
| `SFTP_BATCH_SIZE` | `100` | Files processed per batch |
| `SFTP_MAX_FILE_SIZE_MB` | `1024` | Maximum file size limit |

### Schedule Configuration

- **Default Schedule**: Every hour
- **Catchup**: Disabled (only runs for current time)
- **Max Active Runs**: 1 (prevents concurrent executions)

## Architecture Decisions

### 1. **Abstraction Layer**
- Created `SFTPFileSync` class to abstract SFTP operations
- Easy migration to other data sources (S3, GCS, etc.)
- Separation of business logic from Airflow specifics

### 2. **Scalability Considerations**
- **Batch Processing**: Processes files in configurable batches
- **Chunked Transfer**: Large files transferred in chunks
- **Memory Management**: Avoids loading all file metadata in memory
- **Size Limits**: Configurable file size limits

### 3. **Error Handling**
- **Retry Logic**: 3 retries with exponential backoff
- **Atomic Transfers**: Uses temporary files for atomic operations
- **Graceful Degradation**: Continues processing even if individual files fail
- **Comprehensive Logging**: Detailed logs for troubleshooting

### 4. **Extensibility**
- **Plugin Architecture**: Custom operators in plugins directory
- **Transformation Support**: Easy to add file transformations
- **Monitoring Hooks**: Built-in metrics and health checks

## Extensibility Examples

### Adding File Transformations

The project includes examples for adding transformations:

```python
from plugins.sftp_utilities import SFTPFileTransformOperator, compress_file_transformation

# Use in DAG
transform_task = SFTPFileTransformOperator(
    task_id='compress_and_sync',
    source_conn_id='sftp_source',
    target_conn_id='sftp_target',
    file_path='/path/to/file.txt',
    transformation_function=compress_file_transformation,
    dag=dag
)
```

### Changing Data Sources

To migrate from SFTP to S3, modify the `SFTPFileSync` class:

1. Replace SFTP hooks with S3 hooks
2. Update file listing methods
3. Modify transfer methods
4. DAG logic remains unchanged

## Monitoring and Alerts

### Built-in Monitoring
- Task success/failure tracking
- File transfer statistics
- Performance metrics logging
- Connection health checks

### Custom Metrics
The `SFTPSyncMonitor` class provides:
- Sync statistics
- Success rates
- Performance metrics
- Error tracking

## 🛠️ Troubleshooting

### Common Issues

1. **Connection Failed**
   - Verify SFTP credentials
   - Check network connectivity
   - Validate connection configuration

2. **Permission Denied**
   - Ensure SFTP user has read access to source
   - Ensure SFTP user has write access to target
   - Check directory permissions

3. **Large File Transfers**
   - Increase `SFTP_MAX_FILE_SIZE_MB` variable
   - Monitor disk space on Airflow workers
   - Consider using external file transfer tools for very large files

4. **Memory Issues**
   - Reduce `SFTP_BATCH_SIZE` variable
   - Increase Docker memory limits
   - Monitor worker resource usage

### Logs Location
- Container logs: `docker-compose logs airflow-scheduler`
- Task logs: Available in Airflow Web UI
- File logs: `./logs/` directory

## Performance Optimization

### For Large Scale Operations

1. **Increase Worker Resources**
   ```yaml
   # In docker-compose.yml, add to airflow-worker:
   deploy:
     resources:
       limits:
         memory: 4G
         cpus: '2'
   ```

2. **Optimize Batch Size**
   - Start with default (100)
   - Increase for many small files
   - Decrease for large files

3. **Parallel Processing**
   - Increase Celery worker concurrency
   - Add more worker containers
   - Use Kubernetes executor for auto-scaling

## Security Considerations

1. **Credentials Management**
   - Use Airflow Connections for SFTP credentials
   - Consider using SSH keys instead of passwords
   - Rotate credentials regularly

2. **Network Security**
   - Use VPN or private networks
   - Implement firewall rules
   - Monitor connection logs

3. **Data Privacy**
   - Encrypt sensitive data in transit
   - Implement access controls
   - Audit file access logs

## 🧪 Testing with Included Test Environment

This project includes a complete test environment with two SFTP servers pre-configured for easy testing!

### Quick Test Setup

```bash
# Start test environment with SFTP servers
chmod +x test.sh
./test.sh

# Configure Airflow connections automatically
chmod +x configure-airflow.sh
./configure-airflow.sh
```

The test environment includes:

- **Source SFTP Server** (localhost:2222) - Pre-populated with sample files
- **Target SFTP Server** (localhost:2223) - Destination for synced files
- **Complete Airflow Setup** - Ready to run sync DAGs

## 📝 Disclaimer

This project was developed with AI assistance (GitHub Copilot) for documentation and code writing. However, all AI-generated content has been thoroughly reviewed, understood, and validated by me. I take full responsibility for the implementation and am fully aware of all code and documentation decisions made in this project.

## 📄 License

This project is provided as-is for demonstration and educational purposes.
