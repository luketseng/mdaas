# -*- encoding: utf8-*-
from configparser import ConfigParser
from handler.log_handler import LogHandler
from exception import base
from datetime import datetime, timedelta
from os.path import abspath
import zipfile
import time
import os
import requests
import shutil
import re
import json
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()



config = ConfigParser()
config.read(os.path.join(os.path.abspath(
    os.path.dirname(__file__)), '../config', 'env.conf'))


def is_in_time_log_list(fname):
    return fname in ['PPIN.txt', 'api.log', 'diag.log', 'journalctl_log.txt', 'mst.log', 'shc.log', 'smartctl.txt', 'nvme_list.json']


class MDaaSObj(object):
    def __init__(self):
        self.logger = LogHandler(__name__)
        self.err_flag=None

    def sn_info(self, data):
        ip = data.get('ip')
        sn = data.get('sn')
        if ip and sn:
            sn_folder = self._create_sn_folder(sn)
            url = 'https://%s:5003/mdaas/status' % (ip)
            status_result = self._get_mdaas_data(url)
            status_result = self._gen_deviceTest_history(sn_folder, status_result, ip=ip, sn=sn)
            self._gen_status_file(sn, sn_folder, status_result)
            self._gen_history_file(ip, sn, sn_folder, status_result)
        else:
            raise base.KeyError('lost ip or sn in body')
        return {'result': 'ok'}

    def download_sn(self, data):
        ip = data.get('ip')
        sn = data.get('sn')
        if ip and sn:
            sn_log_folder = self._create_sn_logs_folder(sn)
            sn_blob_folder = self._create_sn_blobs_folder(sn)
            self.sn_info(data)
            self._download_logs(ip, sn, sn_log_folder)
            self._download_blobs(ip, sn, sn_blob_folder)
            zip_path = self._zip_dir(sn)
            return zip_path
        else:
            self.logger.error('lost ip or sn in body')
            raise base.KeyError('lost ip or sn in body')

    def _create_sn_folder(self, sn):
        sn_folder = os.path.join(config.get('setting', 'output'), sn)
        try:
            os.makedirs(sn_folder, exist_ok=True)
        except OSError:
            self.logger.error('Error: Creating directory. ' + sn_folder)
        return sn_folder

    def _create_sn_logs_folder(self, sn):
        sn_log_folder = os.path.join(
            config.get('setting', 'output'), sn, 'logs')
        try:
            os.makedirs(sn_log_folder, exist_ok=True)
        except OSError as e:
            self.logger.error(e)
        return sn_log_folder

    def _create_sn_blobs_folder(self, sn):
        sn_blob_folder = os.path.join(
            config.get('setting', 'output'), sn, 'blobs')
        try:
            os.makedirs(sn_blob_folder, exist_ok=True)
        except OSError as e:
            self.logger.error(e)
        return sn_blob_folder

    def _get_mdaas_data(self, url):
        try:
            response = requests.get(url, verify=False)
            #print(response.status_code)
            if response.status_code != 200:
                raise base.InvalidDataError('Call api fail: ' + url)
            #print(response, type(response))
            #print(response.text, type(response.text))
            #print(response.content, type(response.content))
            content_type = response.headers.get('content-type')
            content_type_text_list = ['application/octet-stream']
            if content_type == 'application/json':
                result = response.json()
            elif 'utf-8' in content_type or content_type in content_type_text_list:
                print("response.headers.get('content-type')", content_type)
                result = response.text
            else:
                print("find new response.headers.get('content-type'): [{}]".format(content_type))
                #result = response.text
                print(type(response.text), len(response.text))
            return result
        except Exception as e:
            raise base.InvalidDataError(e)

    def _save_mdaas_blob_data(self, url, save_path):
        try:
            response = requests.get(url, verify=False)
            if response.status_code != 200:
                raise base.InvalidDataError('Call api fail: ' + url)

            totalbits = 0
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        totalbits += 1024
                        f.write(chunk)
        except Exception as e:
            raise base.InvalidDataError(e)

    def _gen_status_file(self, sn, sn_folder, status_result):
        date = datetime.strptime(status_result.get('detail', {}).get('test_start_time'), "%Y-%m-%dT%H:%M:%S.%fZ")
        test_start_time = date.strftime("%Y%m%d%H%M%S")
        test_expect_time = None
        test_end_time = None
        if status_result.get("history", None):
            end_case_etime = status_result['history'][-1]['etime']
            end_case_date = datetime.strptime(end_case_etime, "%Y-%m-%d %H:%M:%S")
            test_end_time = end_case_date.strftime("%Y%m%d%H%M%S")
            timestamp = str(int(time.mktime(time.strptime(test_end_time, "%Y%m%d%H%M%S"))))
            test_expect_time = str(int(datetime.timestamp(end_case_date+timedelta(hours=8))))
        else:
            test_end_time = test_start_time
            timestamp = str(int(time.mktime(time.strptime(test_start_time, "%Y%m%d%H%M%S"))))
            test_expect_time = str(int(datetime.timestamp(date+timedelta(hours=3))))

        historys = status_result.get('history', [])
        self.err_flag=None
        for idx, history in enumerate(historys):
            if history.get("err_code") != "None" or history.get("err_msg") != "None":
                self.err_flag=True

        mdaas_mode=None if not status_result.get('detail', None) else status_result.get('detail', None).get('mdaas_mode', None)
        test_result = status_result.get('test_result', 'failed')
        if test_result == 'pending':
            test_result = "Pass"
        elif test_result == 'passed' and not self.err_flag:
            test_result = "ResultPass"
        elif test_result == 'passed' and mdaas_mode == 'bsl':
            test_result = "ResultPass"
        #elif test_result == 'failed' and mdaas_mode == 'intelshc' and 'SHC test failed' in str(historys):
        #    test_result = "ResultPass"
        elif test_result == 'failed' or (test_result == 'passed' and self.err_flag):
            test_result = "Fail"
        else:
            test_result = "CheckPoint"

        status_content = "SysLog=%s_%s.log\n" % (sn, test_start_time)
        status_content += "CaseTotalItem=%s\n" % (
            status_result.get('items', 0))
        status_content += "CaseItemID=%s\n" % (status_result.get('current', 0))
        status_content += "ListFileName=%s\n" % (config.get('setting', 'list_file_name'))
        status_content += "CaseClass=%s\n" % (config.get('setting', 'case_class'))
        status_content += "CaseItemName=%s\n" % (status_result.get('desc', "").replace(' ', '_').upper())
        status_content += "CaseStatusID=%s\n" % (status_result.get('current', 0))
        status_content += "CreateTime=%s\n" % (date.strftime("%Y-%m-%dT%H:%M:%S"))
        status_content += "LastResult=%s\n" % (test_result)
        status_content += "TestEndTime=%s\n" % (test_end_time)
        status_content += "TestExpectTime=%s\n" % (test_expect_time)
        status_content += "SFCS_STIME=%s\n" % ("")

        file_path = os.path.join(sn_folder, sn + '.status_' + timestamp)
        self._write_log(file_path, status_content)

    def _gen_deviceTest_history(self, sn_folder, status_result, **kwargs):
        diag_log_dict=dict()
        ip = kwargs.get("ip", None)
        sn = kwargs.get("sn", None)
        if not ip or not sn:
            print("not get ip or sn: ip={} sn={}".format(ip, sn))
            exit()

        # update diag.log
        sn_log_folder = self._create_sn_logs_folder(sn)
        #self._download_logs(ip, sn, sn_log_folder, '/mdaas/log/diag.log')
        self._download_logs(ip, sn, sn_log_folder, status_result=status_result)

        file_path = os.path.join(
            sn_folder, 'logs', 'diag.log')
        with open(file_path, 'r') as fp:
            log = fp.read()
            match = re.findall(r'(?i)(?s)DeviceTest\{\n(.*?\n)\}DeviceTest\n', log)
            if match:
                print("current item from diag.log = {}".format(len(match)))
                #print("current item from status_reslut = {}".format(status_result['items']))
                for i in match:
                    index = match.index(i)
                    des = re.search(r'(?i)(?s)"Description":\s+"(.*?)",', i)
                    stime= re.search(r'(?i)(?s)"Start Time":\s+"(.*?)",', i)
                    etime = re.search(r'(?i)(?s)"EndTime":\s+"(.*?)",', i)
                    if des.group(1) == status_result['history'][index]['desc']:
                        status_result['history'][index]['stime'] = stime.group(1)
                        status_result['history'][index]['etime'] = etime.group(1)
                    else:
                        print('no match desc between log and request')
            else:
                print("not match DeviceTest")
                #print(repr(match))

        # pretty history log
        #file_path_s = os.path.join(
        #    sn_folder, 'logs', 'deviceTest_history.log')
        #with open(file_path_s, 'w') as f:
        #    f.write(json.dumps(status_result, sort_keys=True, indent=4))
        #    f.close()

        return status_result

    def _gen_history_file(self, ip, sn, sn_folder, status_result):
        date = datetime.strptime(status_result.get('detail', {}).get(
            'test_start_time'), "%Y-%m-%dT%H:%M:%S.%fZ")
        test_start_time = date.strftime("%Y%m%d%H%M%S")
        test_start_time_in_content = date.strftime("%Y-%m-%d_%H:%M:%S")
        test_end_time_in_content = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

        history_content = '<Test log>\n<System Info>\nRack Position   :\nRack ID         :\nPosition ID     :\nOperator ID     :\nSerial Number   : %s\nPart Number     :\nNode IP         : %s\nBMC IP          :\nBMC USERNAME    :\nBMC PASSWORD    :\n\n<Test Info>\nStart Time      : %s\nTest List       :\nTest Item       :\nTest ExpectTime :\nTest RunTime    :\nCMDLINE         :\nCONFIG DIR      :\n' % (
            sn, ip, test_start_time_in_content)
        history_content += '========================================================================================================================\n'
        history_content += '<ID>  <Stage>          <Item>                                         <Start time>      <End time>        <Run> <Result>\n'

        history_part=''
        historys = status_result.get('history', [])
        for idx, history in enumerate(historys):
            error_msg=''
            #print(idx, history)
            history_part += str(idx+1).ljust(6)
            history_part += 'MDaaS'.ljust(17)
            if history.get("err_code") != "None" or history.get("err_msg") != "None":
                error_msg = '[{}:{}] '.format(history.get("err_code"), history.get("err_msg").replace(' ', '_')[:30])
                self.err_flag=True
            history_part += '{}{}'.format(history.get('desc', '').replace(' ', '_').upper(), error_msg).ljust(47)
            history_part += history.get('stime', '').replace('-', '').replace(' ', '_').ljust(18)
            history_part += history.get('etime', '').replace('-', '').replace(' ', '_').ljust(18)
            history_part += '1'.rjust(4)
            if history.get('status', 'fail') == 'pass' and history.get("err_code") == "None" and history.get("err_msg") == "None":
                history_part += '  [[32m Pass [0;39m]'
            elif "DISK" in history.get("err_code") and "Temperature" in history.get("err_msg"):
                history_part += '  [[32m Pass [0;39m]'
                self.err_flag=False
            else:
                history_part += '  [[31m Fail [0;39m]'
            history_part += '\n'
        history_content += history_part

        # write history log
        file_path = os.path.join(
            sn_folder, sn + '_history.log')
        self._write_history_log(file_path, history_part)

        if status_result.get('status', 'running') == 'finished':
            history_content += '========================================================================================================================\n'
            if status_result.get('test_result', 'failed') == 'passed' and not self.err_flag:
                history_content += '<RESULT>:[32m PASS [0;39m]'
            else:
                history_content += '<RESULT>:[31m Fail [0;39m]'

        file_path = os.path.join(
            sn_folder, sn + '_' + test_start_time + '.log')
        self._write_log(file_path, history_content)

    def _write_log(self, path, content):
        try:
            with open(path, 'w') as out:
                out.write(content)
                out.close()
        except Exception as e:
            self.logger.error(e)

    def _write_history_log(self, path, content):
        read_history = str()
        if os.path.isfile(path):
            with open(path, 'r') as fr:
                read_history = fr.read()

        try:
            with open(path, 'a+') as out:
                for line in content.split('\n'):
                    if read_history.find(line) == -1:
                        #print(line)
                        out.write(line)
                        out.write('\n')
                out.close()
        except Exception as e:
            self.logger.error(e)

    def _download_logs(self, ip, sn, sn_log_folder, single_file=None, status_result={}):
        print("==== {}".format(single_file))
        test_start_time = ''
        # sn info api will call this one (status_result !={})
        detail = status_result.get('detail', {})
        if status_result:
            date = datetime.strptime(detail.get('test_start_time'), "%Y-%m-%dT%H:%M:%S.%fZ")
            test_start_time = date.strftime("%Y%m%d%H%M%S")
        try:
            if single_file:
                url = 'https://%s:5003%s' % (ip, single_file)
                log_info = self._get_mdaas_data(url)
                if type(log_info) == type(str()):
                    body = log_info
                else:
                    body = log_info.get('body', '')

                file_name = os.path.basename(single_file)
                file_path = os.path.join(sn_log_folder, file_name)
                self._write_log(file_path, body)
            else:
                url = 'https://%s:5003/mdaas/log_list' % (ip)
                log_list = self._get_mdaas_data(url)

                for log_file in log_list.get('log_options', []):
                    if '.bin' in log_file:
                        print('find ".bin" in {}'.format(log_file))
                        continue
                    url = 'https://%s:5003%s' % (ip, log_file)
                    log_info = self._get_mdaas_data(url)
                    if type(log_info) == type(str()):
                        body = log_info
                    elif type(log_info) == type(dict()):
                        body = log_info.get('body', '')
                    elif type(log_info) == type(list()):
                        body = json.dumps(log_info, indent=4)
                    else:
                        print(type(log_info))
                        exit()

                    file_name = os.path.basename(log_file)
                    file_path = os.path.join(sn_log_folder, file_name)
                    self._write_log(file_path, body)
                    if test_start_time and is_in_time_log_list(file_name):
                        file_time_name = file_name.split('.')[0] + "_" + test_start_time + '.' +file_name.split('.')[1]
                        #file_time_path = os.path.join(sn_log_folder, file_time_name)
                        #self._write_log(file_time_path, body)
        except Exception as e:
            self.logger.error(e)
            raise base.FileNotExistError(e)

    def _download_blobs(self, ip, sn, sn_blob_folder):
        try:
            url = 'https://%s:5003/mdaas/blob_list' % (ip)
            blob_list = self._get_mdaas_data(url)

            for blob_file in blob_list.get('blob_options', []):
                url = 'https://%s:5003%s' % (ip, blob_file)
                print(url)
                file_name = blob_file.split('/')[-1]
                file_path = os.path.join(sn_blob_folder, file_name)
                self._save_mdaas_blob_data(url, file_path)
        except Exception as e:
            self.logger.error(e)
            raise base.FileNotExistError(e)

    def _zip_dir(self, sn):
        zip_path = os.path.join(config.get('setting', 'output'), sn)

        zf = zipfile.ZipFile(zip_path + '.zip', 'w', zipfile.ZIP_DEFLATED)

        for root, dirs, files in os.walk(zip_path):
            for file_name in files:
                zf.write(os.path.join(root, file_name))

        return abspath(zip_path + '.zip')
