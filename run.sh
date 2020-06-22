#!/bin/sh

if [ -z "${PORT}" ]; then
  PORT=8080
fi

if [ -z "${IP}" ]; then
  IP="0.0.0.0"
fi

ORIGIN_DIRECTORTY=$(pwd)
BASEDIR=$(dirname "$0")
{
  cd "$BASEDIR"
  gunicorn toad_api.main:toad_api_app --bind $IP:$PORT --worker-class aiohttp.GunicornWebWorker
} ||{
  :
}
cd "$ORIGIN_DIRECTORTY"