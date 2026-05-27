FROM python:3.10-slim

# Set working directory to fpl-auto root so relative paths 'data/...' and 'predictions/...' resolve
# (Pitfall 3: fpl-auto uses hardcoded relative paths from the fpl-auto/ directory)
WORKDIR /app

# Copy entire fpl-auto contents (data/, predictions/, fpl_auto/, fpl_microservice/, etc.)
COPY . .

# Install fpl-auto's own dependencies first, then microservice dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r fpl_microservice/requirements.txt

# Single worker required: fpl-auto uses multiprocessing.Pool internally,
# multiple Uvicorn workers would each spawn their own pools causing resource contention (D-02)
CMD uvicorn fpl_microservice.main:app --host 0.0.0.0 --port 8000 --workers 1
