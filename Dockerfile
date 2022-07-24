FROM python:3.10.4-slim

WORKDIR /chatops

COPY . .

RUN apt update && apt install git -y
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir poetry

RUN poetry config virtualenvs.create false
RUN poetry install

#ENTRYPOINT ["opsdroid"]
#CMD ["start"]
