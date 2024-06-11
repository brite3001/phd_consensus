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
