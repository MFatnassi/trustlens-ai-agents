# Use official lightweight Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Set working directory
WORKDIR /app

# Install Node.js (provides `npx`, required to spawn the Tavily MCP server).
# The Python MCP client launches `npx -y tavily-mcp@latest` as a stdio subprocess,
# so Node must be present in the image or the subprocess spawn fails with
# FileNotFoundError: 'npx'.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g tavily-mcp@latest \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage build cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port (Cloud Run will override the port and inject PORT env var, but this is good practice)
EXPOSE 8080

# Run uvicorn server
CMD uvicorn api:app --host 0.0.0.0 --port $PORT
