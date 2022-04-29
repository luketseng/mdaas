# -*- encoding: utf8-*-
from configparser import ConfigParser
from api import create_app
import os

config = ConfigParser()
config.read(os.path.join(os.path.abspath(
    os.path.dirname(__file__)), './config', 'env.conf'))

app = create_app()

if __name__ == '__main__':
    app.run(
        host=config.get('api', 'ip'),
        port=int(config.get('api', 'port')),
        threaded=True,
        debug=True
    )
