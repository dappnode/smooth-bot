# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy only the necessary files into the container
COPY .env .
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Copy the Python script into the container
COPY twitter.py .

# Run twitter.py when the container launches
CMD ["python", "twitter.py"]
