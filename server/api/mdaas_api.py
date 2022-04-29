# -*- encoding: utf8-*-
from flask import Blueprint, request, make_response, send_file
from api_objects.mdaas_obj import MDaaSObj
from flasgger import swag_from
from exception import base
import json
import os


blueprint = Blueprint('mdaas_api', __name__)
mdaas_obj = MDaaSObj()


@blueprint.route("/mdaas/sn_info", methods=['POST'])
@swag_from('../api_specs/mdaas/sn_info.yml')
def sn_info():
    try:
        info = request.json
        data = mdaas_obj.sn_info(info)
        return make_response(json.dumps(data), 200)
    except Exception as e:
        return make_response("Failure: %s" % str(e), 400)


@blueprint.route("/mdaas/download", methods=['POST'])
@swag_from('../api_specs/mdaas/download_sn.yml')
def download_sn():
    try:
        info = request.json
        zip_path = mdaas_obj.download_sn(info)
        return send_file(zip_path, mimetype='zip', attachment_filename=info.get('sn')+'.zip', as_attachment=True)
    except Exception as e:
        return make_response("Failure: %s" % str(e), 400)
