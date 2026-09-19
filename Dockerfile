# Production Dockerfile for Apify Actor with Playwright & Python 3.11
FROM apify/actor-python-playwright:3.11

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /usr/src/app

# Copy dependency specifications first to leverage Docker layer caching
COPY requirements.txt ./

# Install project dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and actor definitions
COPY . ./

# Set the entrypoint to run the Actor module
CMD ["python3", "-m", "src.main"]
