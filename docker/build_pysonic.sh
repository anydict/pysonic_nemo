#!/bin/bash

# Build image PySonic

SCRIPT_NAME=$(readlink -f "$0")
SCRIPT_PATH=$(dirname "$SCRIPT_NAME")
cd $SCRIPT_PATH || exit
cd ..

read -r first_line < version
version=$(echo "$first_line" | tr -d '[:space:]')

echo "Run build PySonic with version ${version}"

echo Build docker of PySonic, version: ${version}

docker build -t anydict/pysonic:${version} -f $SCRIPT_PATH/Dockerfile .
