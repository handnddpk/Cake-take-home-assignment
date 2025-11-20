FROM apache/airflow:2.9.3

# Switch to root to create directories first
USER root

# Create necessary directories with correct permissions
RUN mkdir -p /opt/airflow/dags /opt/airflow/logs /opt/airflow/plugins /opt/airflow/config && \
    chown -R airflow:root /opt/airflow/dags /opt/airflow/logs /opt/airflow/plugins /opt/airflow/config

# Switch to airflow user for all pip installations
USER airflow

# Install SFTP provider as airflow user
RUN pip install --no-cache-dir apache-airflow-providers-sftp==4.1.0

# Remain as airflow user for runtime (this is the default for the base image)
USER airflow
