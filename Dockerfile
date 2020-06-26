FROM python:3.8

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./toad_api ./toad_api
COPY ./run.sh ./run.sh

RUN mkdir ./config
VOLUME ./config

EXPOSE 8080

CMD ["./run.sh"]

# docker run --network=iotoad_network -p 8080:8080 -v $(pwd)/config:/app/config toad_api