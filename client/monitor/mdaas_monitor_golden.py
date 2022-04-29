#!/usr/bin/python3

import ast
from datetime import datetime, timedelta
import exception as base
import time
import sys
import os
import shutil
import subprocess
from subprocess import STDOUT, check_output
import json
import re
from netaddr import *
from netaddr.core import AddrFormatError
import pymysql.cursors
import pexpect
import requests
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()
# pip install dhcp-leases
from ping3 import ping
from dhcp_leases import DhcpLeases

grub = {
    "MG": "grub_validation.cfg-golden",
    "MD": "grub.cfg",
    "M1": "grub.cfg-L10"
}

DWNLOAD_THRESHOLD = 0.9
INFRA_FOLDER = '/opt/wiwynn/builds/22.3.1/MDaaS_Infra/configs/'



class RM_connecter():
    RK_conn = None

    def __init__(self, ip, *args, **kwargs):
        server = {
            'hostname': ip,
            'port': '22',
            'username': 'root',
            'password': '$pl3nd1D',
        }
        command = 'ssh -p %s %s@%s' % (server['port'], server['username'], server['hostname'])
        process = pexpect.spawn(command, timeout=30)
        #print(f'command: {command}')
        expect_list = [
          'yes/no',
          'password:',
          'WcsCli#',
          pexpect.EOF,
          pexpect.TIMEOUT,
        ]
        index = process.expect(expect_list)
        #print(f'match: {index} => {expect_list[index]}')
        if index == 0:
              process.sendline("yes")
              expect_list = [
                'password:',
                pexpect.EOF,
                pexpect.TIMEOUT,
              ]
              index = process.expect(expect_list)
              #print(f'match: {index} => {expect_list[index]}')
              if index == 0:
                process.sendline(server['password'])
                expect_list = [
                  'WcsCli#',
                  pexpect.EOF,
                  pexpect.TIMEOUT,
                ]
                index = process.expect(expect_list)
                if index == 0:
                    print('{} connect success'.format(ip))
                    #process.interact()
              else:
                print('EOF or TIMEOUT')
                process.close()
        elif index == 1:
            process.sendline(server['password'])
            #process.interact()
            expect_list = [
              'WcsCli#',
              pexpect.EOF,
              pexpect.TIMEOUT,
            ]
            index = process.expect(expect_list)
            if index == 0:
                print('{} connect success\n'.format(ip))
        else:
            print('EOF or TIMEOUT')
            process.close()
        self.RK_conn = process

    def sendline(self, command):
        print('------- send RM command [{}]'.format(repr(command)))
        prompt = ['WcsCli#', pexpect.TIMEOUT]
        timeout = 30
        #self.RK_conn.sendcontrol('c')
        #self.RK_conn.expect(prompt)
        self.RK_conn.sendline(command)
        index = self.RK_conn.expect(prompt, timeout=timeout)
        req = None
        if index == 0:
            req = rk_conn.before.decode()
            time.sleep(1)
        elif index == 1:
            print('pexpect.TIMEOUT: [{}]'.format(command))
            return False

        match = re.search(r'Completion Code: (.*)\r', req)
        if match and match.group(1) == 'Success':
            #print(req)
            return req
        else:
            print('------- Get RM code : {}'.format(match.group(1)))
            status_desc = re.search(r'Status Description: (.*)\r', req)
            if status_desc:
                print('------- {}'.format(status_desc.group()))
        return False

    def CP_sendline(self, command):
        timeout=30
        prompt=['root@localhost:~#', pexpect.EOF, pexpect.TIMEOUT]
        print('------- Send CP command [{}]'.format(repr(command)))
        self.RK_conn.sendcontrol('c')
        self.RK_conn.expect(prompt)
        self.RK_conn.sendline(command)
        index = self.RK_conn.expect(prompt, timeout=timeout)
        if index == 0:
            #return self.RK_conn.before.decode()
            req=self.RK_conn.before.decode()
            print(repr(req))
            #req2=self.RK_conn.after.decode()
            #print(repr(req),repr(req2))
            return req
        else:
            print('pexpect.TIMEOUT: {}'.format(command))
            return False

    def close(self):
        print('Run self.RK_conn.close()', self.RK_conn.args)
        self.RK_conn.close()

class mdaas_tools():
    mdaas_dir_path = os.path.dirname(__file__)
    dir_path = '/home/wmxte'
    tftp_path = '/opt/tftpboot'
    rack_maps_path = os.path.join(dir_path, 'rack_maps')
    sfcs_tool_dir = '/opt/wiwynn/mdaas/server/sfcs_tool'
    getUSN_GLB_py = os.path.join(sfcs_tool_dir, 'GetUSNGenealogyBasic.py')
    chkroute_py = os.path.join(sfcs_tool_dir, 'CheckRoute.py')
    complete_py = os.path.join(sfcs_tool_dir, 'Complete.py')
    uploadUSNInfo_py = os.path.join(sfcs_tool_dir, 'UploadUSNInfoWithUniqueCheckFlag.py')
    rack_maps = dict()
    pass_cnt = int()
    rk_conn = None
    err_flag=None

    def get_cmd_req(self, cmd, *args):
        #print(cmd)
        process = os.popen(cmd)
        req = process.read().strip()
        #print(req)
        process.close()

        return req

    def get_bash_request(self, cmd):
        #print(args, type(args))
        cmd = cmd.split(' ')
        print(cmd)
        try:
            out = subprocess.check_output(cmd,
                #stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
                )
            stdout,stderr = out.communicate(timeout=10)
        except subprocess.CalledProcessError as e:
            return False

        return True
        #import time
        #time.sleep(5)
        #print(out.wait(), str(stdout, 'utf-8'), stderr)

        if out.wait(timeout=10) != 0:
            print('cmd error')
        return str(stdout, 'utf-8')

    def parser_db_info(self, data_str):
        dict_info = dict()
        for l in data_str.split('\n'):
            if l:
                tmp = l.split(' ')
                if tmp[1] not in dict_info.keys():
                    dict_info.update({tmp[1]: {'SN': tmp[2], 'MAC': None, 'IP': None, 'UUT': {}}})
                dict_info[tmp[1]]['UUT'].update({tmp[3]: {'SN': tmp[0]}})
        self.rack_maps = dict_info

        return dict_info

    def parser_db_sys_info(self, *data):
        #print(type(data))
        dict_info = dict()

        for i in data[0]:
            if i[1] not in dict_info.keys():
                dict_info.update({i[1]: {'SN': i[2], 'MAC': None, 'IP': None, 'UUT': {}}})
            dict_info[i[1]]['UUT'].update({'{}-{}'.format(i[3],i[4]): {'SN': i[0].strip()}})
        self.rack_maps = dict_info

        return dict_info

    def mod_UUT_stat(self, sn, stat):
        print('------- modify {} status to {}'.format(sn, stat))

        if os.path.isdir('/opt/logs/{SN}'.format(SN=sn)):
            log_file_path = self.get_cmd_req('ls /opt/logs/{SN}/{SN}.status* -1rt | tail -n1'.format(SN=sn))
            os.system('sed -i "s/LastResult=.*/LastResult={}/g" {}'.format(stat, log_file_path))
            print(self.get_cmd_req('cat {}'.format(log_file_path)))

    def _download_api(self, url): # Waid
        try:
            print('\t\tDownloading Golden Config File from API...' )
            r = requests.get(url, allow_redirects=True, verify=False)
            if r.status_code != 200:
                 print('\t\t->Download Failed from API')
                 return False
            d = r.headers['content-disposition']
            fname = re.findall("filename=(.+)", d)[0]
            file_path = '%s/%s' % (INFRA_FOLDER,fname)
            with open(file_path, "wb") as f: f.write(r.content)
            print('\t\t->Success downloaded golden config file:%s' % file_path)
            return fname
        except Exception as e:
            print('error:%s' % str(e))
            return False


    def _get_mdaas_data(self, url):
        try:
            response = requests.get(url, verify=False, timeout=10)
            if response.status_code != 200:
                print('========== get response.status_code != 200')
                print('========== {} ip: [{}] sn: [{}]'.format(url, ip, sn))
                return None
                #exit()
                #raise base.InvalidDataError('Call api fail: ' + url)
            result = response.json()
            return result
        except requests.exceptions.RequestException as e:
            # catastrophic error. bail.
            #raise SystemExit(e)
            return None
        #except Exception as e:
        #    print('========== Exception occur')
        #    raise base.InvalidDataError(e)
        #    return None

    def _post_mdaas_data(self, url, ip, sn):
        try:
            payload = {'ip': ip, 'sn': sn}
            encoded_data = json.dumps(payload).encode('utf-8')
            headers = {'accept': 'application/json', 'content-type': 'application/json'}
            response = requests.post(url, headers=headers, data=encoded_data)
            if response.status_code != 200:
                print('========== post response.status_code != 200')
                print('========== {} ip: [{}] sn: [{}]'.format(url, ip, sn))
                return None
                #exit()
                #print(response.iter_content(chunk_size=256))
                #raise base.InvalidDataError('Call api fail: ' + url)
            result = response.json()
            return result
        except requests.exceptions.RequestException as e:
            # catastrophic error. bail.
            raise SystemExit(e)
            return None
        #except Exception as e:
        #    print('========== Exception occur')
        #    raise base.InvalidDataError(e)
        #    return None

    def jsonf_dump(self, path, result): # Waid
        with open(path, 'w+') as f:
            f.write(json.dumps(result, sort_keys=True, indent=4))


    def history_has_err(self, result): # Waid
        # scan over result to find if error
        history = result.get('history', [])
        for item in history:
            if item.get("err_code") != "None" or \
               item.get("err_msg") != "None":
                print("[ERROR]\tState error:%s \n\terr_code:%s\nerr_msg:%s" % \
                    (item.get("desc"), item.get("err_code"), item.get("err_msg")))
                return True
        return False



    def check_UUT_status(self, sys_info, sys_info_path): # Waid
        """
            check sys-info file + ping + status API
        """
        sn = sys_info['SN']
        # if sys-info not exist, modify status to disconnected
        if not os.path.isfile(sys_info_path):
            # do something record or disable test sys_info-$i
            print('[ERROR]\tfile:%s not find-> modify status to disconnectd'% sys_info_path)
            self.mod_UUT_stat(sn, 'Disconnect')
            return False

        Id = str(sys_info.get('ID', None))
        sn = sys_info.get('SN', None)
        mac = sys_info.get('MAC', None)
        ip = sys_info.get('IP', None)
        print('\n\tBlade info:\t ID:%s SN:%s MAC:%s IP:%s \t-> get status now...'% (Id, sn, mac, ip))
        if not ip or not ping(ip): return False # if blade ip is not exist, not alived

        # get status API and save to status file
        status_path = os.path.join(os.path.dirname(sys_info_path), '{}.status'.format(sn))
        status_api_url = 'https://{}:5003/mdaas/status'.format(ip)
        result = self._get_mdaas_data(status_api_url)
        if not result: return False
        self.jsonf_dump(status_path, result)

        mdaas_mode = result.get('detail',{}).get('mdaas_mode')
        # get test result and start count passed blades
        test_result = result.get('status')
        if not test_result:
            print('\t\t-> No "status" key was found in query status API')
            return False
        # count pass with gen configs step
        if test_result == 'finished' and not self.history_has_err(result) and mdaas_mode == 'gen_configs':
            print("\t\t-> MDaaS Mode: [%s] finished!" % result.get('detail', {}).get('mdaas_mode'))
            self.pass_cnt += 1
        elif test_result == 'failed':
            print('\t\t-> Gen config fail'.format(Id, sn, ip))
            self.mod_UUT_stat(sn, 'Fail')
        else:
            print('\t\t-> MDaaS Mode: [%s] is "%s"' % (result.get('detail', {}).get('mdaas_mode'), test_result))
        print("\t\t(Blade ID:%s is still alived!)" % Id)
        return True

    def sys_info_path(self, rk_sn, sys_id): # Waid
        return os.path.join(self.dir_path, rk_sn, 'sys_info-{}.txt'.format(sys_id))

    def delete_grubs(self,rk_info):
        rk_sn= rk_info.get('SN', None)
        # look over all UUTs to create link for each UUT
        for k,v in rk_info.get('UUT', {}).items():
            sys_mac = v.get('MAC', None)
            mac = sys_mac.replace(':', '-')
            dst = os.path.join(self.tftp_path, "grub.cfg-01-{}".format(mac))
            os.system("rm -rf %s" % dst)
            if not os.path.isfile(dst):
                print('\t-> Delete grub: %s success!' % dst)


    def create_soft_link(self, rk_info):
        net_lib = network_lib()

        stage = rk_info.get('STAGE', None)
        print("======= Create Soft Link for all Blades (stage:[%s])" % stage)
        rk_sn= rk_info.get('SN', None)
        # look over all UUTs to create link for each UUT
        for k,v in rk_info.get('UUT', {}).items():
            sys_sn = v.get('SN', None)
            sys_id = v.get('ID', None)
            sys_mac = v.get('MAC', None)
            # detect MAC, if not , halt
            if not sys_mac:
                #raise SystemExit('======= SYS_MAC GET FAIL: rk_sn={}, sys_sn:{}'.format(rk_sn, sys_sn))
                print('[ERROR]\tSYS_MAC GET FAIL: rk_sn={}, sys_sn:{}'.format(rk_sn, sys_sn))
                continue
            # start to create soft link
            mac = sys_mac.replace(':', '-')
            dst = os.path.join(self.tftp_path, "grub.cfg-01-{}".format(mac))

            # create soft link by stage if stage in MG/MD/M1
            grub.get(stage) and os.system("rm -rf %s && ln -s %s %s" % (dst, grub[stage], dst))
            if os.path.isfile(dst):
                print('\t-> Create success: %s' % dst)

    def polling_status(self, rk_info, stage): # Waid
        net_lib = network_lib()

        print("\tPolling blades now...")
        rk_sn= rk_info.get('SN', None)
        # look over all UUTs to create link for each UUT
        for k,v in rk_info.get('UUT', {}).items():
            sys_sn = v.get('SN', None)
            sys_id = v.get('ID', None)
            # detect MAC, if not , halt
            if not sys_id:
                print("\t\t-> Blade ID not exist: not match r'(\d+)-\d'")
                continue
            sys_info_file = self.sys_info_path(rk_sn, sys_id)
            # Check UUT alived
            if not self.check_UUT_status(v, sys_info_file):
                print('\t\t-> Blade (PN: %s) not alived' % (v['SN']))
                continue


    def _download_blade_golden_conf(self, blade_info, gconfig_files, cnt): # Waid
        sn = blade_info.get('SN')
        ip = blade_info.get('IP', None)
        blade_id = blade_info.get('ID', None)
        mac = blade_info.get('MAC', None)
        ppn = blade_info.get("PPN")
        bpn = blade_info.get("BPN")

        print("\t\tStart download golden config for blade ID: %s " %blade_id)

        # check bpn and ppn already in infra folder
        for fname in gconfig_files:
            # if bpn and ppn already in folder, skip
            if ppn in fname and bpn in fname:
            #if (ppn and ppn in fname) and (bpn and bpn in fname):
                cnt += 1
                print('\t\t-> Golden config already exist(PPN:%s, BPN:%s). Skip...' % (ppn, bpn))
                return cnt
        if not ip or not ping(ip):
            print('\t\t->Failed to Ping...blade id:%s, mac:%s, IP:%s' % (blade_id, mac, ip))
            return cnt
        # get status API and save to status file
        download_url = 'https://{}:5003/mdaas/configs'.format(ip)
        dwn_fname = self._download_api(download_url)
        if dwn_fname: 
            gconfig_files.append(dwn_fname)
            cnt += 1
        return cnt

    def download_golden_conf(self, rk_info):
        print("\n\t==== Download golden config... ===")
        if not len(rk_info.get('UUT')): return # return if no blade
        golden_config_files = os.listdir(INFRA_FOLDER)
        cnt = 0
        for _, blade_info in rk_info.get('UUT', {}).items():
            cnt = self._download_blade_golden_conf(blade_info, golden_config_files, cnt)

        # downloaded rate threshold =  90%
        pass_perc = float(cnt)/len(rk_info.get('UUT'))
        if pass_perc < DWNLOAD_THRESHOLD:
            print("\t\tdownload percent: %s%% " % pass_perc*100)
            return False
        return True


    def get_RK_GLB(self, sn, *args, **kwargs):
        rk_idx = kwargs['rk_index']
        encoding = 'utf-8'

        # get USN Genealogy
        rk_sn_path = os.path.join(tools.dir_path, rk_sn)
        usn_info_path = os.path.join(rk_sn_path, 'usn_info-{}.txt'.format(sn))
        self.get_cmd_req('python3 {} -s {} | grep -v Line > {}'.format(self.getUSN_GLB_py, sn, usn_info_path))
        time.sleep(1)
        req = None
        try:
            with open(usn_info_path, 'r') as fp:
                req = fp.read()
                fp.close()
        except OSError:
            print("Could not open/read file:", usn_info_path)

        # record UPN
        regex = re.compile(r'UPN.*: \'(.*)\$')
        match = re.search(regex, req)
        if match:
            UPN = match.group(1)
            print('-------- GET UPN: {}'.format(UPN))
            self.rack_maps[rk_idx].update({'UPN': UPN})
        else:
            print('-------- GET UPN FAIL: NOT FOUND IN {}'.format(usn_info_path))
            del self.rack_maps[rk_idx]
            return False

        # get TOTAL_UNIT of rack
        PN_list=dict()
        EX_CPN=None
        rk_layout_path = os.path.join(tools.dir_path, 'rack_layout.json')
        if not os.path.exists(rk_layout_path):
            print('Please check rack_layout.json exist in {}'.format(tools.dir_path))
            exit()
        else:
            with open(rk_layout_path, 'r') as f:
                PN_list = json.load(f)
        #print(PN_list)
        EX_CPN = PN_list.get(UPN, None)
        EX_CPN_Line=list()
        if not EX_CPN:
            UPN_split = re.split(r'M|-', UPN)
            EX_CPN = 'M{}-{}'.format(str(int(UPN_split[1])-1), UPN_split[2])
        elif type(EX_CPN) == type(list()):
            for i in EX_CPN:
                EX_CPN_Line.extend(re.findall("CPN.*:.*{}.\w+'(}})".format(i), req))
                #print(EX_CPN_Line)
        else:
            EX_CPN_Line = re.findall("CPN.*:.*{}.\w+'(}})".format(EX_CPN), req)
            #print(len(EX_CPN_Line), EX_CPN_Line, UPN)
        print('-------- EX_CPN: {}'.format(EX_CPN))

        total_unit = len(EX_CPN_Line)
        print('-------- Total units: {}'.format(total_unit))
        #print('-------- [Debug] Total units: {}'.format(total_unit))
        if total_unit < 1:
            print('-------- TOTAL_UNIT of UPN NOT FIND IN {}'.format(usn_info_path))
            del self.rack_maps[rk_idx]
            return False
        self.rack_maps[rk_idx].update({'TOTAL_UNIT': total_unit})

        return True

    def get_rack_stage(self, sn, **kwargs):
        rk_idx = kwargs['rk_index']
        print('\n======== Check Rack Stage Now... =====')

        # get USN Genealogy
        rk_sn_path = os.path.join(tools.dir_path, rk_sn)
        usn_info_path = os.path.join(rk_sn_path, 'usn_info-{}.txt'.format(sn))
        self.get_cmd_req('python3 {} -s {} | grep -v Line > {}'.format(self.getUSN_GLB_py, sn, usn_info_path))
        time.sleep(1)
        req = None
        try:
            with open(usn_info_path, 'r') as fp:
                req = fp.read()
                fp.close()
        except OSError:
            print("\tCould not open/read file:", path)

        # check rk stage
        regex = re.compile(r'Next Process Stage:(.*)')
        match = re.search(regex, req)
        if match:
            stage = match.group(1).strip()
            self.rack_maps[rk_idx].update({'STAGE': stage})

    def check_RK_stage(self, sn, *args, **kwargs):
        rk_idx = kwargs['rk_index']
        print('\n======== Check Rack Stage Now... =====')

        # get USN Genealogy
        rk_sn_path = os.path.join(tools.dir_path, rk_sn)
        usn_info_path = os.path.join(rk_sn_path, 'usn_info-{}.txt'.format(sn))
        self.get_cmd_req('python3 {} -s {} | grep -v Line > {}'.format(self.getUSN_GLB_py, sn, usn_info_path))
        time.sleep(1)
        req = None
        try:
            with open(usn_info_path, 'r') as fp:
                req = fp.read()
                fp.close()
        except OSError:
            print("\tCould not open/read file:", path)
     
        # check rk stage
        regex = re.compile(r'Next Process Stage:(.*)')
        match = re.search(regex, req)
        if match:
            stage = match.group(1).strip()
            #stage = 'MG'
            #if stage == 'MD':
            #    req = self.get_cmd_req('python3 {} -s {}'.format(self.chkroute_py, rk_sn))
            #    regex = re.compile(r"CheckRouteResult.*:.*OK'")
            #    if re.search(regex, req):
            #        print('-------- CheckRouteResult: OK (rack at MD stage)')
            #        self.rack_maps[rk_idx].update({'STAGE': stage})
            #    else:
            #        print('-------- FAIL TO CheckRouteResult: Please check CheckRouteResult for MD stage')
            #        del self.rack_maps[rk_idx]
            #        return False
            # temp pre-talk stage
            #elif stage == 'MG':
            print('\t %s SN:%s is at [%s] Stage\n'%(k, rk_sn, stage))
            if stage == 'MG':
                self.rack_maps[rk_idx].update({'STAGE': stage})
            #elif stage == 'M1':
            #    self.rack_maps[rk_idx].update({'STAGE': stage})
            elif stage == 'WB':
                self.rack_maps[rk_idx].update({'STAGE': stage})
                del self.rack_maps[rk_idx]
                #rk_sn_path = os.path.join(tools.dir_path, rk_sn)
                if os.path.exists(rk_sn_path):
                    try:
                        shutil.rmtree(rk_sn_path)
                    except OSError as e:
                        print("Error: %s - %s." % (e.filename, e.strerror))
                return False
            else:
                print('\t->%s (%s) is not at [MG] stage, since stage is at [%s]\n'%(k, rk_sn, match.group(1)))
                del self.rack_maps[rk_idx]
                return False
            UPN = self.rack_maps[rk_idx]['UPN']
        else:
            print('\t[ERROR] NOT FOUND "Next Process Stage" NOT IN {}'.format(usn_info_path))
            del self.rack_maps[rk_idx]
            return False

        return True

    def pxe_boot(self, rk_info, *args, **kwargs):

        print("------- RUN pxe_boot(rk_info)")
        #print(rk_info)
        rk_sn= rk_info.get('SN', None)
        # look over all UUTs to create link for each UUT
        for k,v in rk_info.get('UUT', {}).items():
            sys_sn = v.get('SN', None)
            sys_id = v.get('ID', None)
            sys_mac = v.get('MAC', None)
            sys_model = v.get('MODEL', None)
            sys_pxe = v.get('PXE', True)
            sys_ip = v.get('IP', None) 

            if not sys_pxe:
                print("------- SKIP PXE") 
                continue

            if sys_model == 'C2080':
                soc_ip=None

                command='set system cmd -i{} -c fru print {}'.format(sys_id, 1)
                req_CP = rk_conn_tools.sendline(command)
                #print(req_CP)
                match = re.search(r'Product Extra.*: (\S+)\r\n', req_CP)
                if match:
                    mac=match.group(1)[:12]
                    soc_mac = net_lib.EUI_mac(mac, formatting=mac_unix_expanded)
                    #print(mac, soc_mac)
                    if not soc_mac:
                        print('-------- soc mac format error: {}'.format(soc_mac))
                        continue
                    soc_ip = network_lib().get_ip_from_leases(soc_mac)
                    print('-------- soc ip: {}'.format(soc_ip))
                    #req += "soc_ip: {}\n".format(soc_ip)
                else:
                    print(repr(req_CP))

                if soc_ip:
                    tools.get_cmd_req('ssh-keygen -R {}'.format(soc_ip))
                    cmd="sshpass -p overlake ssh -o StrictHostKeyChecking=no ovl@{} 'ls -a'".format(soc_ip)
                    tools.get_cmd_req(cmd)

                    cmd="sshpass -p overlake scp /opt/wiwynn/mdaas/client/monitor/Auto_reconfig/Script/* ovl@{}:~/".format(soc_ip)
                    print(cmd)
                    r=tools.get_cmd_req(cmd)
                    print(r)

                    #cmd="sshpass -p overlake ssh -o StrictHostKeyChecking=no ovl@{} 'ls -a'".format(soc_ip)
                    #r=tools.get_cmd_req(cmd)
                    #print(r)

                    cmd="sshpass -p overlake ssh -o StrictHostKeyChecking=no ovl@{} 'sudo -S <<< 'overlake' bash CP_autoReconfig.sh'".format(soc_ip)
                    print(cmd)
                    r=tools.get_cmd_req(cmd)
                    print(r)
                    time.sleep(20)

            command='set system cmd -i {} -c power cycle'.format(sys_id)
            #print(command)
            req = rk_conn_tools.sendline(command)

    def check_rk_alived(self, sn, *args, **kwargs):
        rk_sn = sn
        rk_idx = kwargs['rk_index']
        net_lib = network_lib()

        # get USN Genealogy
        rk_sn_path = os.path.join(tools.dir_path, rk_sn)
        if not os.path.exists(rk_sn_path):
            os.makedirs(rk_sn_path)
            os.chown(rk_sn_path, 1001, 1002)

        usn_info_path = os.path.join(rk_sn_path, 'usn_info-{}.txt'.format(sn))
        #print(self.getUSN_GLB_py, sn, usn_info_path)
        self.get_cmd_req('python3 {} -s {} | grep -v Line > {}'.format(self.getUSN_GLB_py, sn, usn_info_path))
        time.sleep(3)
        req = None
        try:
            with open(usn_info_path, 'r') as fp:
                output = fp.read()
                fp.close()
        except OSError:
            print("Could not open/read file:", usn_info_path)
            exit()

        # check rk mac
        #regex = re.compile(r"CSN.*'(.*)',.*CPN.*RACK MANAGER MAC 1")
        regex = re.compile(r"CSN.*'(.*)',.*CPN.*RACK MANAGER MAC") # Waid
        match = re.search(regex, output)
        if match:
            rk_mac = match.group(1)
            mac = net_lib.EUI_mac(rk_mac, formatting=mac_unix_expanded)
            ip = net_lib.get_ip_from_leases(mac)
            print("======== GET {} MAC={}, IP={}".format(rk_idx, mac, ip))
            if ip:
                # check RK IP connect
                if net_lib.ping(ip):
                    print('-------- {} SN: [{}], PING [{}]: PASS\n'.format(rk_idx, rk_sn, ip))
                    self.rack_maps[rk_idx].update({'MAC': mac, 'IP': ip})
                else:
                    print('-------- {} SN: [{}], PING [{}]: FAIL\n'.format(rk_idx,rk_sn, ip))
                    print('-------- {} IP Disconnect: SET U27 Disconnect'.format(k))
                    UUT_SN = v['UUT']['27-1']['SN']
                    self.mod_UUT_stat(v['UUT']['27-1']['SN'], 'Disconnect')
                    del self.rack_maps[rk_idx]
                    return False
            else:
                print('======== FAIL to GET {} IP FROM dhcp.leases [SN:{} IP: {}]'.format(rk_idx, rk_sn, ip))
                del self.rack_maps[rk_idx]
                return False
        else:
            print("======== FAIL to GET {} SN:{} MAC FAIL VIA self.getUSN_GLB_py".format(rk_idx, rk_sn))
            del self.rack_maps[rk_idx]
            return False

        return True

    def parser_sys_info(self, path):
        output = None
        dict_out = dict()
        
        try:
            with open(path, 'r') as fp:
                output = fp.read()
                fp.close()

            regex = re.compile(r"(?i)(?s)Id: (\d+)\n.*Mac Address: (\S+)\n.*Model: (\S+)\n.*SerialNumber: (\w+)\n")
            match = re.search(regex, output)

            if not match:
                os.remove(path)
                return False
            dict_out['sys_id'] = int(match.group(1)) if match and int(match.group(1)) == i else match
            mac = match.group(2)
            dict_out['sys_mac'] = net_lib.EUI_mac(mac, formatting=mac_unix_expanded)
            dict_out['sys_sn'] = match.group(4) if match else match
            dict_out['sys_ip'] = net_lib.get_ip_from_leases(dict_out['sys_mac'])
            dict_out['model'] = match.group(3) if match else None

            regex = re.compile(r"(?i)(?s)PXE: False")
            #print(output)
            match = re.search(regex, output)
            #print(match)
            dict_out['pxe'] = False if match else True 
            #print(dict_out)
            #sys.exit()

            return dict_out

        except OSError:
            print("Could not open/read file:", path)
            exit()

    def parser_sys_fru(self, path):
        output = None
        dict_out = dict()
        
        try:
            with open(path, 'r') as fp:
                output = fp.read()
                fp.close()


            regex = re.compile(r"(?i)(?s)Board Part Number\s+: (\S+)\n.*Product Part Number\s+: (\S+)\n")
            match = re.search(regex, output)
            if not match:
                #print(repr(output))
                print('\t\t[ERROR] not find BPN and PPN in fru. Remove:%s now' % path)
                os.remove(path)
                return False
            dict_out['sys_bpn'] = match.group(1) if match else match
            dict_out['sys_ppn'] = match.group(2) if match else match

            #print(dict_out)
            return dict_out 

        except OSError:
            print("Could not open/read file:", path)
            exit()

    def re_config_CP(self, ip, index):
        i=index
        print('======== Run re-config function')
        rk_conn_tools_CP = RM_connecter(rk_ip)
        rk_conn_CP = rk_conn_tools_CP.RK_conn

        command='start serial session -i {} -b {}'.format(i, 1)
        rk_conn_CP.sendline(command)
        rk_conn_CP.sendline('')
        time.sleep(3)
        index = rk_conn_CP.expect(['root@localhost:~#', 'WcsCli#', pexpect.TIMEOUT])
        if index == 0:
            print('======== SUCCESS to into CP SOC')
            command='ifconfig'
            if not rk_conn_tools_CP.CP_sendline(command):
                return False

            command='lsmod'
            result=rk_conn_tools_CP.CP_sendline(command)
            if not result:
                return False
            match = re.search(r'catapult ', result)
            #print('------- Match: {}'.format(match))
            if match:
                print('------- CP driver installed')
                command='fpgadiagnostics -reconfigapp'
                result=rk_conn_tools_CP.CP_sendline(command)
                if not result:
                    return False
                match = re.search(r'RECONFIGURATION SUCCEEDED', result)
                if match:
                    print('------- RECONFIGURATION SUCCEEDED')
            else:
                command='modprobe catapult'
                result=rk_conn_tools_CP.CP_sendline(command)
                if not result:
                    return False
                match = re.search(r'loading Catapult FPGA driver', result)
                if match:
                    print('------- loading Catapult FPGA driver')

                command='fpgadiagnostics -reconfigapp'
                result=rk_conn_tools_CP.CP_sendline(command)
                if not result:
                    return False
                match = re.search(r'RECONFIGURATION SUCCEEDED', result)
                if match:
                    print('------- RECONFIGURATION SUCCEEDED')

        elif index == 1:
            print('-------- FAIl to into CP SOC')
            print(rk_conn_CP.before.decode())
            return False
        elif index == 2:
            print('pexpect.TIMEOUT: show system info -i {} -b {}'.format(i, 1))
            #rk_conn.close()
            return False

        rk_conn_tools_CP.close()
        print('-------- Success to re-config')
        return True

class network_lib():

    def ping(self, ip):
        #need to use ping package

        req = tools.get_cmd_req('ping -n -c2 -w5 {}'.format(ip))
        match = re.search(r'2 packets transmitted, 2 received', req)
        #print(req)

        return match

    def get_ip_from_leases(self, mac):
        dhcp_leases = DhcpLeases('/var/lib/dhcpd/dhcpd.leases').get_current()
        dhcp_messages_file = '/var/log/messages'

        lease_obj = dhcp_leases.get(mac, None)
        #print(mac, dhcp_messages_file, lease_obj)
        ip = tools.get_cmd_req('grep -i "{}" {} -B 2 |grep -i DHCPACK |awk \'{{print $(F+8)}}\' |tail -n 1'.format(mac, dhcp_messages_file))

        if lease_obj or ip:
            print(lease_obj, ip)
            if ip:
                return ip
            elif lease_obj:
                return lease_obj.ip
        else:
            print('lease_obj: {}, ip from /var/log/messages: {}'.format(repr(lease_obj), repr(ip)))
            return None

    def EUI_mac(self, mac, formatting=mac_unix_expanded):
        EUI_obj = None

        try:
            EUI_obj = EUI(mac, dialect=formatting)
        except (ValueError, core.AddrFormatError) as e:
            print('======== {}'.format(e))
            return None
            #raise(e)

        return str(EUI_obj)

class pymysql_tools():
    dbconnection = None

    def __init__(self, *args, **kwargs):

        self.dbconnection = pymysql.connect(
            host = "127.0.0.1",
            user = "root",
            password = "password",
            db = "mfg"
        )

    def db_query(self, query, act='select', *args):
        result = None

        try:
            with self.dbconnection.cursor() as cursor:
                cursor.execute(query)
                if act == 'select':
                    result=cursor.fetchall()
                elif act == 'insert':
                    print('===== INSERT SYS DATA\n{}'.format(query))
                    self.dbconnection.commit()
                elif act == 'delete':
                    print('===== DELETE SYS DATA\n{}'.format(query))
                    self.dbconnection.commit()
        except pymysql.Error as e:
            print("========= Caught a Programming Error: ============")
            print(e.args[0], e.args[1])
            # Rollback in case there is any error
            self.dbconnection.rollback()
            return False
        finally:
            return result

    def select_rk_nd_info(self, *args, **kwargs):
        #print(args[0])
        bypass_rk_arg = args[0]
        query = 'SELECT n.node_sn, r.rack_position, r.rack_sn, n.lower_unit, n.slot_id FROM sn_nodes n, sn_racks r WHERE n.rack_sn=r.rack_sn AND r.deleted_at is null {} order by r.rack_position, n.lower_unit;'.format(bypass_rk_arg)

        return self.db_query(query)

if __name__ == '__main__':
    tools = mdaas_tools()
    pymysql_tools = pymysql_tools()
    net_lib = network_lib()
    bypass_rk = list("RK-{}".format(str((i+100))[1:]) for i in []+[]+list(range(1,21)))
    for i in sys.argv[1:]:
        bypass_rk.remove('RK-{}'.format(str((int(i)+100))[1:]))
    bypass_rk_str = str()
    for i in bypass_rk:
        bypass_rk_str += 'AND r.rack_position!="{}" '.format(i)

    # init
    req = pymysql_tools.select_rk_nd_info(bypass_rk_str)
    tools.parser_db_sys_info(req)

    rack_maps = tools.rack_maps.copy()
    for k,v in rack_maps.items():
        rk_sn = v['SN']
        rk_ip = None
        rk_upn = None
        exp_sys_count = None
        rk_stage= None

        # check rk_sn have blank
        if bool(re.search("\s", rk_sn)):
            print('======== Site TE check {} scan-in SN:[{}] have blank'.format(k, rk_sn))
            del tools.rack_maps[k]
            continue

        # check rack alive (mac, ip, connect)
        if not tools.check_rk_alived(rk_sn, rk_index=k):
            continue
        rk_ip = tools.rack_maps[k]['IP']

        # mkdir RK_SN
        rk_sn_path = os.path.join(tools.dir_path, rk_sn)
        if not os.path.exists(rk_sn_path):
            os.makedirs(rk_sn_path)
            os.chown(rk_sn_path, 1001, 1002)

        # rack layout prepare
        src_path = os.path.join(tools.mdaas_dir_path, 'rack_layout.json')
        rk_layout_path = os.path.join(tools.dir_path, 'rack_layout.json')
        if not os.path.exists(rk_layout_path):
            print('move latout to {}'.format(rk_layout_path))
            if os.path.exists(src_path):
                shutil.copy(src_path, rk_layout_path)
                os.chown(rk_layout_path, 1001, 1002)
            else:
                print('Please check default rack_layout.json exist')
                exit()

        print('======== START CHECK RACK INFO {} SN:{} IP:{}'.format(k, rk_sn, rk_ip))
        # get RK info (UPN, TOTAL_UNIT, STAGE)
        if not tools.get_RK_GLB(rk_sn, rk_index=k):
            continue
        # ++++++++++++++ define new stage(MG) for pre-test control disable other stage
        # -> change this function
        if not tools.check_RK_stage(rk_sn, rk_index=k):
            continue

        rk_upn = tools.rack_maps[k]['UPN']
        exp_sys_count = tools.rack_maps[k]['TOTAL_UNIT']
        rk_stage = tools.rack_maps[k]['STAGE']
        rk_conn_tools = RM_connecter(rk_ip)
        rk_conn = rk_conn_tools.RK_conn
        #print(rk_ip, rk_upn, exp_sys_count, rk_stage)
        
        # set unit range
        unit_region = list(range(3,25))+list(range(27,48))
        #unit_region = list(range(16,20))

        # update sys_info-*.txt
        sys_file_count = int(tools.get_cmd_req('ls {}/sys_info-* -l | wc -l'.format(rk_sn_path)))
        print("-------- There are {} file in {}".format(sys_file_count, rk_sn_path))
        print(sys_file_count, exp_sys_count)
        if sys_file_count != exp_sys_count:
        #if True:
            tools.get_cmd_req('ssh-keygen -R {}'.format(rk_ip))
            #db_insert_range = list()

            for i in unit_region:
                sys_file_path = os.path.join(rk_sn_path, 'sys_info-{}.txt'.format(i))
                if not os.path.exists(sys_file_path):
                    command = 'show system info -i {}'.format(i)
                    req = rk_conn_tools.sendline(command)
                    if req:
                        # Save current sys info
                        print('------- Save current sys info {}'.format(sys_file_path))
                        with open(sys_file_path, 'w+') as fp:
                            fp.write(req)
                            fp.close()
                        #db_insert_range.append(i)
                else:
                    cmd="grep -i 'PXE:' {}".format(sys_file_path)
                    if not tools.get_cmd_req(cmd):
                        print('------- Disable PXE sys info {}'.format(sys_file_path))
                        with open(sys_file_path, 'a') as fp:
                            fp.write('PXE: False')
                            fp.close()

                fru_file_path = os.path.join(rk_sn_path, 'sys_fru-{}.txt'.format(i))
                if not os.path.exists(fru_file_path):
                    command = 'set system cmd -i {} -c fru print 0'.format(i)
                    req = rk_conn_tools.sendline(command) 
                    if req:
                        # Save current sys info
                        print('------- Save current sys info {}'.format(fru_file_path))
                        with open(fru_file_path, 'w+') as fp:
                            fp.write(req)
                            fp.close()
                else:
                    # do special case on this
                    pass

            # READY FOR INSERT SYS INFO
            model_name = 'c2030-1u'
            query = 'SELECT id FROM models WHERE name = "{}"'.format(model_name)
            model_id = pymysql_tools.db_query(query)[0][0]
            #print('model ID = {}'.format(model_id))

            #query = 'delete FROM sn_nodes WHERE rack_sn like "{}" and lower_unit != 27;'.format(rk_sn)
            #pymysql_tools.db_query(query)
            for i in unit_region:
                path = os.path.join(tools.dir_path, rk_sn, 'sys_info-{}.txt'.format(i))
                fru_path = os.path.join(tools.dir_path, rk_sn, 'sys_fru-{}.txt'.format(i))
                sys_key = '{}-1'.format(i)
                sys_id =  None
                sys_mac = None
                sys_sn = None
                sys_ip = None
                sys_ppn = None
                sys_bpn = None

                if not os.path.exists(path):
                    sys_id = i
                    sys_sn = '{}_CHK_RM_CONNECT'.format(i)
                    continue
                else:
                    dict_out = tools.parser_sys_info(path)
                    if not dict_out:
                        if sys_key in tools.rack_maps[k]['UUT']: del tools.rack_maps[k]['UUT'][sys_key]
                        #os.remove(path)
                        continue
                    #print(dict_out)
                    sys_id = dict_out['sys_id'] 
                    sys_mac = dict_out['sys_mac']
                    sys_sn = dict_out['sys_sn'] 
                    sys_ip = dict_out['sys_ip'] 
                    sys_model = dict_out['model'] 
                    sys_pxe = dict_out['pxe'] 

                    if not sys_mac:
                        os.remove(path)
                        continue
                        #raise ValidationError("Please specify a valid MAC address.")

                    if sys_ip or sys_model == 'C2080':
                        tools.rack_maps[k]['UUT']['{}-1'.format(i)]={'ID': sys_id, 'SN': sys_sn, 'MAC': sys_mac, 'IP': sys_ip, 'MODEL': sys_model, 'PXE': sys_pxe}
                    else:
                        print('======== ip = {}, ID:{} SN:{} not find ip from test server'.format(sys_ip, sys_id, sys_sn))

                    dict_fru_out = tools.parser_sys_fru(fru_path)
                    if dict_fru_out and sys_key in tools.rack_maps[k]['UUT']:
                        sys_bpn = dict_fru_out['sys_bpn'] 
                        sys_ppn = dict_fru_out['sys_ppn'] 
                        tools.rack_maps[k]['UUT']['{}-1'.format(i)].update({'BPN': sys_bpn, 'PPN': sys_ppn})
                #print(sys_id, sys_mac, sys_sn, sys_ip)
                query = 'SELECT * FROM sn_nodes WHERE rack_sn like "{}" and lower_unit = {};'.format(rk_sn, sys_id)
                result = pymysql_tools.db_query(query)

                if (sys_id != 27 and not result) or sys_sn not in repr(result):
                    #query = 'delete FROM sn_nodes WHERE node_sn like "{}";'.format(sys_sn)
                    query = 'delete FROM sn_nodes WHERE rack_sn like "{}" and lower_unit = "{}";'.format(rk_sn, sys_id)
                    pymysql_tools.db_query(query, act='delete')
                    time.sleep(1)
                    data = '("{}","{}","{}","{}","1","{}",{},now(),now());'.format(sys_sn, rk_sn, sys_id, sys_id, 'auto_script', model_id)
                    query = 'INSERT INTO sn_nodes (node_sn, rack_sn, lower_unit, higher_unit, slot_id, oper_id, model_id, created_at, updated_at) VALUES {}'.format(data)
                    pymysql_tools.db_query(query, act='insert')

            # for new stage delay
            if sys_file_count < exp_sys_count // 2 :
                t = 120
                print('======= wait {} sec for new stage'.format(t))
                time.sleep(t)

        else:
            flag = True
            if flag:
                model_name = 'c2030-1u'
                query = 'SELECT id FROM models WHERE name = "{}"'.format(model_name)
                model_id = pymysql_tools.db_query(query)[0][0]
            #print(json.dumps(tools.rack_maps, sort_keys=True, indent=4))

            print('sys_info-* count = {}, use exist {} dir\n'.format(sys_file_count, rk_sn_path))
            for i in unit_region:
                path = os.path.join(tools.dir_path, rk_sn, 'sys_info-{}.txt'.format(i))
                fru_path = os.path.join(tools.dir_path, rk_sn, 'sys_fru-{}.txt'.format(i))

                if not os.path.isfile(path):
                    continue
                else:
                    dict_out = tools.parser_sys_info(path)
                    if not dict_out:
                        #os.remove(path)
                        continue
                    #print(dict_out)
                    sys_id = dict_out['sys_id'] 
                    sys_mac = dict_out['sys_mac']
                    sys_sn = dict_out['sys_sn'] 
                    sys_ip = dict_out['sys_ip'] 
                    sys_model = dict_out['model'] 
                    sys_pxe = False# dict_out['pxe'] 

                    #print(sys_id, sys_mac, sys_sn, sys_ip)
                    sys_key = '{}-1'.format(i)
                    if sys_ip:
                        tools.rack_maps[k]['UUT'][sys_key]={'ID': sys_id, 'SN': sys_sn, 'MAC': sys_mac, 'IP': sys_ip, 'MODEL': sys_model, 'PXE': sys_pxe}
                    else:
                        print('======== ip = {}, ID:{} SN:{} not find ip from test server'.format(sys_ip, sys_id, sys_sn))
                        print('======== Remove dict key')
                        if sys_key in tools.rack_maps[k]['UUT']: del tools.rack_maps[k]['UUT'][sys_key]
                        #continue
                        #exit()

                    dict_fru_out = tools.parser_sys_fru(fru_path)
                    if dict_fru_out and sys_key in tools.rack_maps[k]['UUT']:
                        sys_bpn = dict_fru_out['sys_bpn'] 
                        sys_ppn = dict_fru_out['sys_ppn'] 
                        tools.rack_maps[k]['UUT']['{}-1'.format(i)].update({'BPN': sys_bpn, 'PPN': sys_ppn})
                #print(sys_id, sys_mac, sys_sn, sys_ip)
                    #print(dict_out)
                #print(sys_id, sys_mac, sys_sn, sys_ip)

                query = 'SELECT * FROM sn_nodes WHERE rack_sn like "{}" and lower_unit = {};'.format(rk_sn, sys_id)
                result = pymysql_tools.db_query(query)
                #print("++++", bool(result), type(result), result)
                #print("++++", bool(sys_sn), type(sys_sn), sys_sn)
                #print("====", bool(sys_sn not in result[0]))
                if (sys_id != 27 and not result) or sys_sn not in repr(result):
                #if sys_id != 27 and flag and not result:
                    #query = 'delete FROM sn_nodes WHERE node_sn like "{}";'.format(sys_sn)
                    query = 'delete FROM sn_nodes WHERE rack_sn like "{}" and lower_unit = "{}";'.format(rk_sn, sys_id)
                    pymysql_tools.db_query(query, act='delete')
                    time.sleep(1)
                    data = '("{}","{}","{}","{}","1","{}",{},now(),now());'.format(sys_sn, rk_sn, sys_id, sys_id, 'auto_script', model_id)
                    query = 'INSERT INTO sn_nodes (node_sn, rack_sn, lower_unit, higher_unit, slot_id, oper_id, model_id, created_at, updated_at) VALUES {}'.format(data)
                    pymysql_tools.db_query(query, act='insert')

        # make soft link and pxe
        print(json.dumps(tools.rack_maps, sort_keys=True, indent=4))
        rk_info = tools.rack_maps[list(tools.rack_maps.keys())[0]]
        tools.create_soft_link(rk_info)
        tools.pxe_boot(rk_info)
        rk_conn_tools.close()

    #print(json.dumps(tools.rack_maps, sort_keys=True, indent=4))
    #sys.exit()
    #os.system("echo '{}' > {}".format(json.dumps(tools.rack_maps, sort_keys=True, indent=4), tools.rack_maps_path))
    os.system("echo '{}' > {}".format(json.dumps(tools.rack_maps, sort_keys=True, indent=4), '/opt/logs/rack_maps.txt'))

    if (tools.rack_maps):
        print('Rack content:\n')
        print(json.dumps(tools.rack_maps, sort_keys=True, indent=4))
        print('\n======== Start Polling Blade Status....======')
    else:
        print('\tNothing to do..')


    # START MONITIOR
    for k,v in tools.rack_maps.items():
        tools.pass_cnt = 0
        rk_sn = v['SN']
        e_pass_cnt = tools.rack_maps[k].get('TOTAL_UNIT', None)
        #tools.check_RK_stage(rk_sn, rk_index=k)
        stage = tools.rack_maps[k].get('STAGE', None)
        if stage != 'MG': #Waid
            print("\tNot in golden config stage, move on next rack...")
            continue
        tools.polling_status(v, stage) 


        # ++++++++++++++ add logic for golden cfg save and next stage

        # ====== to do set_node_info_sh function: export $SN.status & update sys ip, sn to mdaas & check PASS_CNT
        print('\n\t======= Rack Summary ===========')
        print('\tRK SN: {}'.format(rk_sn))
        print('\tCount of total blades:\t%s' %(e_pass_cnt))
        print('\tCount of passed blades:\t%s'% (tools.pass_cnt))
        print('\tNext... check all passed or not')
        #if True: # Waid DEV
        if tools.pass_cnt == e_pass_cnt:# and match
            print('\t->All blade passed, now downloading golden config...')
            # Waid
            # download golden config
            tools.download_golden_conf(v)
            # get current stage
            tools.check_RK_stage(rk_sn, rk_index=k)

            # download zip to /opt/logs/
            for x,y in v['UUT'].items():
                timestamp = tools.get_cmd_req('date +%s')
                path = "/opt/logs/{SN}-{STAGE}-{T}.zip".format(SN=y['SN'], STAGE=stage, T=timestamp)
                print('\t======= Download test log: {}'.format(path))
                tools.get_cmd_req('curl -X POST "http://127.0.0.1:9796/api/v1/mdaas/download" -H "accept: application/json" -H "Content-Type: application/json" -d \'{{"ip": "{}", "sn":"{}"}}\' -o {}'.format(y.get('IP'), y.get('SN'), path))
                # upload USN info
                req = tools.get_cmd_req('python3 {} -s {} -t {}'.format(tools.uploadUSNInfo_py, y['SN'], stage))
                regex = re.compile(r"UploadUSNInfoWithUniqueCheckFlagResult.*:.*OK'")
                match = re.search(regex, req)
                if not match:
                    print('\t------- FAIL to upload USN info [{}, {}]'.format(y['SN'], stage))


            print('\n======= Move current stage (%s) to next stage....' % stage)
            req = tools.get_cmd_req('python3 %s -s %s -t %s' % (tools.complete_py, rk_sn, stage))
            regex = re.compile(r"CompleteResult.*:.*OK'")
            match = re.search(regex, req)
            if not match:
                print('[ERROR]\tFAIL to move from:[%s] to [MD] stage' % stage)
                continue
            print('\tMoved SFCS stage success...')
            # success to move stage
            #tools.check_RK_stage(rk_sn, rk_index=k)
            tools.get_rack_stage(rk_sn, rk_index=k)
            n_stage = tools.rack_maps[k].get('STAGE', None)
            print('\tCurrent SFCS stage:[%s], original stage:[%s]' % (n_stage, stage))
            if n_stage == stage: # if it is still the same original stage
                print('\tFAIL to move from:%s to MD SFCS stage' % stage)
            else:
                print('\tSuccess: %s, SN:%s moved to %s' % (k, rk_sn, n_stage))
            rk_sn_path = os.path.join(tools.dir_path, rk_sn)
            # DEV tmp removed
            try:
                # Remove grub
                shutil.rmtree(rk_sn_path)
                tools.delete_grubs(rk_info)
            except OSError as e: print("\tError: %s - %s." % (e.filename, e.strerror))

        else:
            print("\n\tNot all blades of the rack passed. Continue next monitoring...")

