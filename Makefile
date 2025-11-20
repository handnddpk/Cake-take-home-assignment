.PHONY: help setup start stop restart logs clean test health test-env test-start test-stop test-clean test-config config demo

# Default target
help:
	@echo "Available commands:"
	@echo ""
	@echo "Main Application:"
	@echo "  setup       - Initialize the project"
	@echo "  start       - Start all services"
	@echo "  stop        - Stop all services"
	@echo "  restart     - Restart all services"
	@echo "  logs        - Show logs for all services"
	@echo "  health      - Check service health"
	@echo "  clean       - Clean up containers and volumes"
	@echo "  config      - Configure Airflow connections and variables"
	@echo "  demo        - Show demo information and access points"
	@echo ""
	@echo "Development/Testing:"
	@echo "  test-env    - Start test environment with SFTP servers"
	@echo "  test-config - Configure Airflow for testing"
	@echo "  test-start  - Start test environment"
	@echo "  test-stop   - Stop test environment"
	@echo "  test-clean  - Clean up test environment completely"
	@echo "  test        - Run complete test setup (env + config)"

# Setup the project
setup:
	@echo "🚀 Setting up SFTP File Sync project..."
	@chmod +x setup.sh
	@./setup.sh

# Start all services
start:
	@echo "🚀 Starting SFTP File Sync Demo..."
	@chmod +x create-demo-data.sh
	@./create-demo-data.sh
	@docker-compose up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 45
	@echo "⚙️  Configuring Airflow..."
	@make config
	@echo ""
	@echo "✅ 🎯 DEMO IS READY!"
	@echo ""
	@echo "📊 Access Points:"
	@echo "   🌐 Airflow UI: http://localhost:8080 (airflow/airflow)"
	@echo "   📁 Source SFTP: localhost:2222 (sourceuser/sourcepass)"
	@echo "   📁 Target SFTP: localhost:2223 (targetuser/targetpass)"
	@echo ""
	@echo "🎬 Demo Steps:"
	@echo "   1. Open Airflow UI and enable the 'sftp_file_sync' DAG"
	@echo "   2. Click the play button to trigger the DAG"
	@echo "   3. Watch files transfer from source to target SFTP"
	@echo "   4. Verify results in target SFTP server"

# Stop all services
stop:
	@echo "🛑 Stopping all services..."
	@docker-compose down

# Restart all services
restart: stop start

# Show logs
logs:
	@echo "📋 Showing logs..."
	@docker-compose logs -f

# Check service health
health:
	@echo "🏥 Checking service health..."
	@docker-compose ps
	@echo ""
	@echo "Airflow Web UI: http://localhost:8080"
	@curl -s -o /dev/null -w "Airflow Web UI: %{http_code}\n" http://localhost:8080/health || echo "Airflow Web UI: Not accessible"

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	@docker-compose down -v --remove-orphans
	@docker system prune -f

# Configure Airflow connections and variables
config:
	@echo "⚙️  Configuring Airflow..."
	@chmod +x configure-airflow.sh
	@./configure-airflow.sh

# Run tests (placeholder for future test implementation)
test: test-env test-config
	@echo "✅ Test environment is ready!"
	@echo "Access Airflow UI at http://localhost:8080 (airflow/airflow)"
	@echo "See TESTING.md for detailed testing instructions"

# Test environment commands
test-env: test-start

test-start:
	@echo "🧪 Starting test environment..."
	@chmod +x test.sh
	@./test.sh

test-config:
	@echo "⚙️  Configuring Airflow for testing..."
	@chmod +x configure-airflow.sh
	@./configure-airflow.sh

test-stop:
	@echo "🛑 Stopping test environment..."
	@docker-compose down

test-clean:
	@echo "🧹 Cleaning up test environment..."
	@docker-compose down -v --remove-orphans
	@rm -rf test-data/target/* || true
	@echo "✅ Test environment cleaned"

# Show demo information
demo:
	@echo "🎯 SFTP File Sync Demo Status"
	@echo ""
	@echo "📊 Access Points:"
	@echo "   🌐 Airflow UI: http://localhost:8080 (airflow/airflow)"
	@echo "   📁 Source SFTP: localhost:2222 (sourceuser/sourcepass)"
	@echo "   📁 Target SFTP: localhost:2223 (targetuser/targetpass)"
	@echo ""
	@echo "📁 Demo Files Available:"
	@find test-data/source -type f -name "*.csv" -o -name "*.json" -o -name "*.txt" | head -10
	@echo ""
	@echo "🎬 Demo Steps:"
	@echo "   1. Open Airflow UI and enable the 'sftp_file_sync' DAG"
	@echo "   2. Click the play button to trigger the DAG"
	@echo "   3. Watch files transfer from source to target SFTP"
	@echo "   4. Verify results in target SFTP server"
	@echo ""
	@echo "🔧 Useful Commands:"
	@echo "   make logs    - View service logs"
	@echo "   make health  - Check service status"
	@echo "   make stop    - Stop demo"
