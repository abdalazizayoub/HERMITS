# Use a lightweight Python base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements files from both sub-packages
COPY backend/requirements.txt ./backend_reqs.txt
COPY agent/requirements.txt ./agent_reqs.txt

# Install all dependencies
RUN pip install --no-cache-dir -r backend_reqs.txt -r agent_reqs.txt

# Copy the entire project code into the container
COPY . .

# Expose the port that server.py uses and docker-compose maps
EXPOSE 8080

# Run the unified server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
