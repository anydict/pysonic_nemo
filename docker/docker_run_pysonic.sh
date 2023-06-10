#!/bin/bash

# Run instance with number 2 with version image PySonic 1.0.0
# bash docker_run_pysonic.sh 2 1.0.0

if [ -z "$1" ]; then
  echo "There is no instance number. Use 0-9. Example docker_run_pysonic 2" && exit 0
else
  instance_name=pysonic-$1
fi

if [ -z "$2" ]; then
  echo "There is no version" && exit 0
else
  version=$2
fi

if [ -f "/usr/bin/docker" ]; then
  docker_path="/usr/bin/docker"
elif [ -f "/run/host/bin/docker" ]; then
  docker_path="/run/host/bin/docker"
else
  echo "No found docker in /usr/bin/docker or /run/host/bin/docker" && exit 0
fi

${docker_path} stop "$instance_name"
${docker_path} rm "$instance_name"

host_conf_path="/usr/local/etc/$instance_name" && mkdir -p $host_conf_path
host_logs_path="/opt/$instance_name" && mkdir -p $host_logs_path
host_sounds_path="/var/lib/asterisk/sounds/en/custom" && mkdir -p $host_sounds_path

${docker_path} run \
  -d \
  --restart=always \
  --net=host \
  -v "$host_logs_path":"$host_logs_path" \
  -v "$host_conf_path":"$host_conf_path" \
  -v "$host_sounds_path":"$host_sounds_path" \
  -v /tmp/:/tmp/ \
  --name "$instance_name" \
  anydict/pysonic:"$version"
