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
    pyserial \
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

# Create working directory
WORKDIR /workspace

# Copy ATS node test execution code
COPY ats_node_test/ /workspace/ats_node_test/
COPY entrypoint.sh /workspace/entrypoint.sh

# Make entrypoint executable
RUN chmod +x /workspace/entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace

# Results directory (mounted by Jenkins)
ENV RESULTS_DIR=/workspace/results

# Default entrypoint
ENTRYPOINT ["/workspace/entrypoint.sh"]

