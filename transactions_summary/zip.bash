#! /bin/bash

cd pip_packages
zip -r /zip/my_deployment_package.zip .
cd ..
zip /zip/my_deployment_package.zip txns.py