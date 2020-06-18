FROM python:3.8

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./toad_api ./toad_api
COPY ./run.sh ./run.sh

RUN mkdir ./config
VOLUME ./config

EXPOSE 80

CMD ["./run.sh"]

# docker run --network=iotoad_network -p 80:80 -v $(pwd)/config:/app/config toad_api