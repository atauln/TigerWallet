FROM docker.io/python:3.8-buster
LABEL maintainer="Ata Noor <>an9965@g.rit.edu>"

WORKDIR /app
ADD ./ /app
COPY ./requirements.txt requirements.txt
RUN apt-get -yq update && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /app/

CMD [ "gunicorn", "--bind", "0.0.0.0:8080", "app:app"]