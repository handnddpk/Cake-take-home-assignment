#!/bin/bash

# Script to automatically configure Airflow connections and variables for testing

echo "🔧 Configuring Airflow for SFTP Sync Testing..."

# Wait for Airflow to be ready
echo "Waiting for Airflow webserver to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0
until docker-compose exec -T airflow-webserver airflow version &>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "❌ Airflow webserver failed to become ready after ${MAX_RETRIES} attempts"
        exit 1
    fi
    echo "Waiting for Airflow webserver... (attempt $RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done
echo "✅ Airflow webserver is ready!"
sleep 5  # Extra buffer to ensure all services are stable

# Function to create/update Airflow connection using CLI
create_connection() {
    local conn_id=$1
    local conn_type=$2
    local host=$3
    local login=$4
    local password=$5
    local port=$6
    local extra=$7
    
    echo "Creating connection: $conn_id"
    docker-compose exec -T airflow-webserver \
        airflow connections delete "$conn_id" 2>/dev/null || true
    
    docker-compose exec -T airflow-webserver \
        airflow connections add "$conn_id" \
        --conn-type "$conn_type" \
        --conn-host "$host" \
        --conn-login "$login" \
        --conn-password "$password" \
        --conn-port "$port" \
        --conn-extra "$extra"
}

# Function to set Airflow variable
set_variable() {
    local key=$1
    local value=$2
    
    echo "Setting variable: $key = $value"
    docker-compose exec airflow-webserver \
        airflow variables set "$key" "$value"
}

echo ""
echo "Creating SFTP connections..."

# Create source SFTP connection
create_connection \
    "sftp_source" \
    "ssh" \
    "sftp-source" \
    "sourceuser" \
    "sourcepass" \
    "22" \
    '{"no_host_key_check": true}'

# Create target SFTP connection
create_connection \
    "sftp_target" \
    "ssh" \
    "sftp-target" \
    "targetuser" \
    "targetpass" \
    "22" \
    '{"no_host_key_check": true}'

echo ""
echo "Setting Airflow variables..."

# Set required variables
set_variable "SFTP_SYNC_ROOT_DIR" "/upload"
set_variable "SFTP_BATCH_SIZE" "100"
set_variable "SFTP_MAX_FILE_SIZE_MB" "1024"
set_variable "COMPRESSION_THRESHOLD_MB" "10"

echo ""
echo "✅ Airflow configuration completed!"
echo ""
echo "You can now:"
echo "1. Access Airflow UI at http://localhost:8080"
echo "2. Enable the 'sftp_file_sync' DAG"
echo "3. Trigger the DAG to start file synchronization"
echo ""
