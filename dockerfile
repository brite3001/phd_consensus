# FROM python:3.10

# WORKDIR /code

# # Copy files into the container
# COPY logs.py /code/
# COPY requirements.txt /code/
# COPY start.py /code/

# ADD tensorflow_lite /code/tensorflow_lite/
# ADD helpers /code/helpers/
# ADD outgoing_message_functions /code/outgoing_message_functions
# ADD incoming_message_functions /code/incoming_message_functions
# ADD event_loops /code/event_loops
# ADD start_helpers /code/start_helpers

# RUN mkdir -p /code/ipc/repreq/
# RUN mkdir -p /code/ipc/pubsub/

# RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt


# CMD ["python3", "/code/start.py"]

FROM python:3.10

WORKDIR /code

# copy code
COPY src /code/src/

# copy pdm stuff
COPY .pdm-python /code/
COPY pdm.lock /code/
COPY pyproject.toml /code/


RUN curl -sSL https://pdm-project.org/install-pdm.py | python3 -
RUN export PATH=/root/.local/bin:$PATH
RUN /root/.local/bin/pdm install

CMD ["/root/.local/bin/pdm", "run", "src/main.py"]
