#!/bin/bash

# Create additional demo files and directories

echo "📁 Creating additional demo data..."

# Create nested directories with files
mkdir -p test-data/source/reports/2024/Q1
mkdir -p test-data/source/reports/2024/Q2
mkdir -p test-data/source/backups

# Create report files
cat > test-data/source/reports/2024/Q1/sales_q1.csv << 'EOF'
month,revenue,units_sold,region
Jan,125000,450,North
Feb,138000,520,North
Mar,142000,580,North
EOF

cat > test-data/source/reports/2024/Q2/sales_q2.csv << 'EOF'
month,revenue,units_sold,region
Apr,155000,620,North
May,168000,680,North
Jun,172000,720,North
EOF

# Create backup files
cat > test-data/source/backups/config_backup.txt << 'EOF'
# System Configuration Backup
# Generated: 2024-01-20
server.port=8080
database.url=jdbc:postgresql://localhost:5432/app
cache.enabled=true
EOF

echo "✅ Demo data created successfully!"
echo "📊 Files ready for SFTP sync demonstration"
