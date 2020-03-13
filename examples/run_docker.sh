#!/bin/sh

# In order to work, script must be places in the root directory; e.g. toad_api/build_docker.sh

ORIGIN_DIRECTORTY=$(pwd)
BASEDIR=$(dirname "$0")
{
  cd "$BASEDIR"
  sudo docker run -d -it --name api_server -p 80:8080 -v "$(pwd)"/config:/usr/src/toad_api/config toad_api
} ||{
  :
}
cd "$ORIGIN_DIRECTORTY"

