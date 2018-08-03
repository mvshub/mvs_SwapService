#!/bin/bash

sudo apt-get install -y mysql-server
sudo apt-get install -y libmysqlclient-dev
sudo apt-get install -y python-mysqldb
sudo apt-get install -y python3-pip

sudo -H pip3 install --upgrade pip

sudo -H pip3 install mysqlclient

sudo -H pip3 install gevent
sudo -H pip3 install pycrypto

sudo -H pip3 install flask
sudo -H pip3 install flask-sqlalchemy
sudo -H pip3 install sqlalchemy-utils
sudo -H pip3 install flask-migrate
sudo -H pip3 install flask-bootstrap
sudo -H pip3 install flask-wtf
