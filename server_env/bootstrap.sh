#!/bin/bash

set -x

# Set local time
export TZ="Asia/Taipei"
ln -snf /usr/share/zoneinfo/$TZ /etc/localtime
echo $TZ > /etc/timezone
dpkg-reconfigure -f noninteractive tzdata

export PYTHONPATH=/root/server

# run supervisord
/usr/bin/supervisord
service supervisor restart

