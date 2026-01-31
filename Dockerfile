FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Create directories for data and sessions
RUN mkdir -p /app/data /app/sessions

# Set environment
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "-m", "src.main"]
