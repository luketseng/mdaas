# encoding:utf8
from flask import Flask, request, jsonify
from exception import base
from flask_cors import CORS
from flasgger import Swagger
from configparser import ConfigParser
from handler.log_handler import LogHandler
from api.mdaas_api import blueprint as mdaas_bp
from datetime import datetime
import json
import os

config = ConfigParser()
config.read(os.path.join(os.path.abspath(
    os.path.dirname(__file__)), '../config', 'env.conf'))


def handle_internal(e):
    return str(e), 500


def handle_bad_request(e):
    return str(e), 400


def handle_forbidden(e):
    return str(e), 401


def handle_unauthorized(e):
    return str(e), 403


def handle_not_found(e):
    return str(e), 404


def create_app():
    app = Flask(__name__)
    CORS(app, supports_credentials=True)
    logger = LogHandler(__name__)
    app.config['SWAGGER'] = {'uiversion': 3}
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    # 註冊 api
    app.register_blueprint(mdaas_bp, url_prefix='/api/v1')

    # error handling
    app.errorhandler(base.FileNotExistError)(handle_not_found)
    app.errorhandler(base.ItemNotExistError)(handle_not_found)
    app.errorhandler(base.FileTypeError)(handle_bad_request)
    app.errorhandler(base.DataDeletedError)(handle_bad_request)
    app.errorhandler(base.ObjectAttributeError)(handle_bad_request)
    app.errorhandler(base.InvalidDataError)(handle_bad_request)
    app.errorhandler(base.FileTypeError)(handle_bad_request)
    app.errorhandler(base.DataTypeError)(handle_bad_request)
    app.errorhandler(base.UnauthorizedError)(handle_unauthorized)
    app.errorhandler(Exception)(handle_internal)

    Swagger(app)


    @app.after_request
    def activity_log(response):
        try:
            if request.method not in ['GET', 'OPTIONS']:
                token = request.headers.get('Token')
                if token:
                    data = request.get_json()
                    dt = datetime.today()
                    created = dt.strftime("%Y/%m/%d %H:%M:%S")
                    log_data = {
                        'api': request.path,
                        'method': request.method,
                        'request_data': data,
                        'response_time': created,
                        'status_code': response._status_code,
                        'response': str(response.response)
                    }
                    logger.info(log_data)
        except Exception as e:
            logger.error(e)
        return response

    return app
