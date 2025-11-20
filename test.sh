#!/bin/bash

# SFTP File Sync - Test Script
# This script helps test the complete SFTP sync solution with test SFTP servers

set -e

echo "🧪 SFTP File Sync - Test Environment Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Check prerequisites
echo "Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi
print_success "Docker is installed"

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi
print_success "Docker Compose is installed"

echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    print_info "Creating .env file from .env.example..."
    cp .env.example .env
    
    # Set AIRFLOW_UID for Linux users
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "AIRFLOW_UID=$(id -u)" >> .env
        print_success "Set AIRFLOW_UID=$(id -u) for Linux"
    else
        print_success "Using default AIRFLOW_UID=50000 for non-Linux OS"
    fi
else
    print_success ".env file already exists"
fi

echo ""

# Create test data directories
print_info "Creating test data directories..."
mkdir -p test-data/source/a/b/c
mkdir -p test-data/source/data/2024/03
mkdir -p test-data/target
mkdir -p test-config
mkdir -p logs dags plugins config

print_success "Test directories created"

echo ""

# Set appropriate permissions for Linux
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    print_info "Setting directory permissions for Linux..."
    sudo chown -R $(id -u):$(id -g) test-data logs dags plugins config test-config
    print_success "Directory permissions set"
    echo ""
fi

# Stop any running containers
print_info "Stopping any existing containers..."
docker-compose down -v 2>/dev/null || true
print_success "Cleaned up existing containers"

echo ""

# Start test environment
print_info "Starting test environment (SFTP servers + Airflow)..."
docker-compose up -d sftp-source sftp-target redis

# Wait for SFTP servers to be ready
echo ""
print_info "Waiting for SFTP servers to be ready..."
sleep 5

# Test SFTP connections
echo ""
print_info "Testing SFTP server connections..."

# Test source SFTP
if nc -z localhost 2222 2>/dev/null; then
    print_success "Source SFTP server is accessible on port 2222"
else
    print_error "Source SFTP server is not accessible"
    echo "Run: docker-compose logs sftp-source"
    exit 1
fi

# Test target SFTP
if nc -z localhost 2223 2>/dev/null; then
    print_success "Target SFTP server is accessible on port 2223"
else
    print_error "Target SFTP server is not accessible"
    echo "Run: docker-compose logs sftp-target"
    exit 1
fi

echo ""

# Initialize Airflow
print_info "Initializing Airflow..."
docker-compose up airflow-init

if [ $? -eq 0 ]; then
    print_success "Airflow initialization completed"
else
    print_error "Airflow initialization failed"
    exit 1
fi

echo ""

# Start Airflow services
print_info "Starting Airflow services (Scheduler, Worker, Web Server)..."
docker-compose up -d airflow-webserver airflow-scheduler airflow-worker airflow-triggerer

echo ""
print_info "Waiting for Airflow to be ready (this may take a minute)..."
sleep 15

# Check Airflow health
MAX_RETRIES=12
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health | grep -q "200"; then
        print_success "Airflow Web UI is healthy and ready!"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            print_error "Airflow Web UI failed to start after ${MAX_RETRIES} retries"
            echo "Check logs with: docker-compose logs airflow-webserver"
            exit 1
        fi
        echo "Waiting for Airflow... ($RETRY_COUNT/$MAX_RETRIES)"
        sleep 5
    fi
done

echo ""
echo "=========================================="
echo "🎉 Test Environment is Ready!"
echo "=========================================="
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""
echo "🔗 Access Points:"
echo "  • Airflow Web UI: http://localhost:8080"
echo "    Username: airflow"
echo "    Password: airflow"
echo ""
echo "  • Source SFTP: localhost:2222"
echo "    Username: testuser"
echo "    Password: testpass"
echo ""
echo "  • Target SFTP: localhost:2223"
echo "    Username: targetuser"
echo "    Password: targetpass"
echo ""
echo "📁 Test Data Location:"
echo "  • Source: ./test-data/source/"
echo "  • Target: ./test-data/target/"
echo ""
echo "⚙️  Next Steps:"
echo "  1. Configure SFTP connections in Airflow UI:"
echo ""
echo "     Connection 1 - Source SFTP:"
echo "       Connection Id: sftp_source"
echo "       Connection Type: SSH"
echo "       Host: sftp-source"
echo "       Username: testuser"
echo "       Password: testpass"
echo "       Port: 22"
echo "       Extra: {\"key_file\": \"\", \"no_host_key_check\": true}"
echo ""
echo "     Connection 2 - Target SFTP:"
echo "       Connection Id: sftp_target"
echo "       Connection Type: SSH"
echo "       Host: sftp-target"
echo "       Username: targetuser"
echo "       Password: targetpass"
echo "       Port: 22"
echo "       Extra: {\"key_file\": \"\", \"no_host_key_check\": true}"
echo ""
echo "  2. Set Airflow Variables:"
echo "       SFTP_SYNC_ROOT_DIR: /upload"
echo "       SFTP_BATCH_SIZE: 100"
echo "       SFTP_MAX_FILE_SIZE_MB: 1024"
echo ""
echo "  3. Enable and trigger the 'sftp_file_sync' DAG"
echo ""
echo "  4. Monitor sync progress in Airflow UI"
echo ""
echo "  5. Verify files in target: ls -laR test-data/target/"
echo ""
echo "🛠️  Useful Commands:"
echo "  • View all logs: docker-compose logs -f"
echo "  • View Airflow logs: docker-compose logs -f airflow-scheduler"
echo "  • Stop all: docker-compose down"
echo "  • Clean up: docker-compose down -v"
echo "  • Connect to source SFTP: sftp -P 2222 testuser@localhost"
echo "  • Connect to target SFTP: sftp -P 2223 targetuser@localhost"
echo ""
echo "For detailed instructions, see README.md"
echo ""
