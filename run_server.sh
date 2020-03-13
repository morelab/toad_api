#!/bin/sh

ORIGIN_DIRECTORTY=$(pwd)
BASEDIR=$(dirname "$0")
{
  cd "$BASEDIR"
  gunicorn toad_api.main:toad_api_app --bind 0.0.0.0:8080 --worker-class aiohttp.GunicornWebWorker
} ||{
  :
}
cd "$ORIGIN_DIRECTORTY"