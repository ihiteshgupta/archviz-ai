# ArchViz AI - API Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and build LibreDWG from source for DWG to DXF conversion
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    automake \
    autoconf \
    libtool \
    texinfo \
    && rm -rf /var/lib/apt/lists/* \
    # Build LibreDWG from source
    && cd /tmp \
    && git clone --depth 1 https://github.com/LibreDWG/libredwg.git \
    && cd libredwg \
    && sh autogen.sh \
    && ./configure --disable-bindings \
    && make -j$(nproc) \
    && make install \
    && ldconfig \
    && cd / && rm -rf /tmp/libredwg

# Copy project files
COPY pyproject.toml .
COPY README.md .
COPY core/ ./core/
COPY api/ ./api/

# Install Python dependencies
RUN pip install --no-cache-dir .

# Create directories for uploads and output
RUN mkdir -p uploads output

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
