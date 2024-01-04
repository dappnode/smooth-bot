# Stage 1: Build stage
FROM python:3.8-slim AS builder

# Set the working directory in the build stage
WORKDIR /build

# Copy only the necessary files for installing dependencies
COPY requirements.txt .

# Install dependencies
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.8-slim

# Set the working directory in the runtime stage
WORKDIR /app

# Copy only the necessary files into the runtime stage
COPY --from=builder /usr/local/lib/python3.8/site-packages /usr/local/lib/python3.8/site-packages
COPY twitter.py .

# Run twitter.py when the container launches
CMD ["python", "twitter.py"]
