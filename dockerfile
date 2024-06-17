FROM python:3.10

WORKDIR /code

COPY pyproject.toml pdm.lock /code/

# Install PDM
RUN pip install pdm

# Install dependencies
RUN pdm install


COPY src /code/src/

# Set environment variable to disable output buffering
ENV PYTHONUNBUFFERED=1


CMD ["pdm", "run", "src/main.py"]
