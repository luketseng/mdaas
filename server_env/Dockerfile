FROM python:3.8.3-slim

# add image user to root
USER root

RUN set -x \
    && apt-get -y update \
    && apt-get install -y vim iputils-ping \
    && apt-get install -y nginx gunicorn3 tzdata wget sshpass\
    && apt-get install -y supervisor python3-gevent\
    && apt install -y python3-numpy python3-scipy python3-matplotlib

# Install python modules
COPY server_env/requirements.txt /tmp
RUN set -x && pip3 install -r /tmp/requirements.txt

# Setup nginx
COPY server_env/server.conf /etc/nginx/sites-available/
RUN set -x \
    && rm /etc/nginx/sites-enabled/default \
    && ln -s /etc/nginx/sites-available/server.conf /etc/nginx/sites-enabled/server.conf\
    && echo "daemon off;" | tee -a /etc/nginx/nginx.conf
    
# Copy supervisor.conf
COPY server_env/supervisor.conf /etc/supervisor/conf.d/supervisor.conf

# Add bootstrap script and make it executable
COPY server_env/bootstrap.sh /root/bootstrap.sh
RUN chown root:root /root/bootstrap.sh && chmod a+x /root/bootstrap.sh

# Copy server source code to python path
COPY server /root/server
RUN mkdir -p /root/server/output
WORKDIR /root/server
ENV TZ=Asia/Taipei

ENTRYPOINT ["/root/bootstrap.sh"]
