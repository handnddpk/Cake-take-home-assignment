#!/bin/bash

# SFTP File Sync - Setup Script
# This script helps set up the Airflow environment for SFTP file synchronization

set -e

echo "🚀 Setting up SFTP File Sync project..."

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    
    # Set AIRFLOW_UID for Linux users
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "AIRFLOW_UID=$(id -u)" >> .env
        echo "✅ Set AIRFLOW_UID=$(id -u) for Linux"
    else
        echo "✅ Using default AIRFLOW_UID=50000 for non-Linux OS"
    fi
else
    echo "✅ .env file already exists"
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs dags plugins config

# Set appropriate permissions for Linux
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo chown -R $(id -u):$(id -g) logs dags plugins config
    echo "✅ Set directory permissions"
fi

# Initialize Airflow
echo "🔧 Initializing Airflow..."
docker-compose up airflow-init

# Check if initialization was successful
if [ $? -eq 0 ]; then
    echo "✅ Airflow initialization completed successfully"
else
    echo "❌ Airflow initialization failed"
    exit 1
fi

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Start the services: docker-compose up -d"
echo "2. Access Airflow UI: http://localhost:8080"
echo "3. Login with username: airflow, password: airflow"
echo "4. Configure SFTP connections in Admin > Connections"
echo "5. Set variables in Admin > Variables"
echo "6. Enable and run the 'sftp_file_sync' DAG"
echo ""
echo "For detailed instructions, see README.md"
