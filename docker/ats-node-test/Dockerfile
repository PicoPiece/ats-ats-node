# ATS Node Test Execution Container
# This container owns ALL hardware interaction: flashing, USB detection, test execution
# Jenkins must NOT do any of these - it only runs this container

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    build-essential \
    python3-pip \
    python3-dev \
    minicom \
    screen \
    usbutils \
    udev \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install --no-cache-dir \
    esptool \
    pyserial \
    pyyaml \
    pytest \
    pytest-html

# Copy ATS node test execution code to /app (separate from workspace)
COPY ats_node_test/ /app/ats_node_test/
COPY entrypoint.sh /app/entrypoint.sh

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Results directory (mounted by Jenkins)
ENV RESULTS_DIR=/workspace/results

# Default entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

