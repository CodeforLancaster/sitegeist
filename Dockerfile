FROM python:3
COPY . /app
WORKDIR /app
#RUN apk add --no-cache bash
RUN ./setup.sh

ENTRYPOINT [ "python", "./main.py"]