FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script
COPY OCRVL_Tester.py .

# Environment variables setup
ENV INPUT_CSV="./data_lake/stat/pdf_triage_stats.csv"
ENV OUTPUT_DIR="./output_VL_merged"
ENV VLLM_URL="http://localhost:8118/v1"
ENV TEST_MODE="false"

# Run the python script
CMD ["python", "OCRVL_Tester.py"]
