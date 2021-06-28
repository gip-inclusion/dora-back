FROM python:3.9-slim-buster
ENV PYTHONUNBUFFERED 1
RUN apt update
RUN apt install -y git

WORKDIR /app

COPY ./requirements requirements
RUN pip install -r requirements/dev.txt

