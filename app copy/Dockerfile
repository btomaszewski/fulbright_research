# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.9-slim

EXPOSE 8080

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install FFmpeg and other dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    python3-dev \
    libpq-dev \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# First create the model directories
RUN mkdir -p /app/models/ner_model_package
RUN mkdir -p /app/models/vector_model_package/sentence_transformer


# Install pip requirements
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

# Download SpaCy model
RUN python -m spacy download en_core_web_sm

# Set environment variables to point to models
ENV NER_MODEL_PATH=/app/models/ner_model_package
ENV VECTOR_MODEL_PATH=/app/models/vector_model_package
ENV PYTHONPATH=/app


# Copy Python code files
COPY *.py /app/

# Copy the model files with proper structure preserving
# Explicitly copy each part of the model to ensure they're all included
COPY models/ner_model_package /app/models/ner_model_package/
COPY models/vector_model_package/*.json /app/models/vector_model_package/
COPY models/vector_model_package/sentence_transformer /app/models/vector_model_package/sentence_transformer/

# Add debugging - list files to verify everything is copied
RUN echo "Files in app directory:" && ls -la /app
RUN echo "Files in vector model directory:" && ls -la /app/models/vector_model_package
RUN echo "Files in sentence transformer directory:" && ls -la /app/models/vector_model_package/sentence_transformer

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# Set environment variable for production
ENV FLASK_ENV=cloudRun

# During debugging, this entry point will be overridden.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "0", "app:app"]