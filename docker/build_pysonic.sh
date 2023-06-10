#!/bin/bash

# Build image PySonic
cd ..

read -r first_line < ../file.txt
version=$(echo "$first_line" | tr -d '[:space:]')

echo Build docker of PySonic, version: ${version}

docker build -t anydict/pysonic:${version} -f Dockerfile ../../pysonic_nemo
