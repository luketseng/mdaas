#!/usr/bin/python3

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
from dhcp_leases import DhcpLeases

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

    def _get_mdaas_data(self, url):
        try:
            response = requests.get(url, verify=False)
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

    def check_UUT_alived(self, sys_info, path, act):
        sn = sys_info['SN']
        #print(sys_info)
        #print(sn, path, os.path.dirname(path), os.path.basename(path))

        if not os.path.isfile(path):
            # do something record or disable test sys_info-$i
            print('------- {} not find: modify UUT status'.format(path))
            self.mod_UUT_stat(sn, 'Disconnect')
            return False

        Id = str(sys_info.get('ID', None))
        sn = sys_info.get('SN', None)
        mac = sys_info.get('MAC', None)
        ip = sys_info.get('IP', None)
        print('======= SYS INFO: {} {} {} {}'.format(Id, sn, mac, ip))
        if not ip:
            return False

        # check SYS ping OK
        ping_req = self.get_cmd_req('ping -n -c2 -w5 {}'.format(ip))
        # try to output journalctl -a to /opt/logs
        cmd="sshpass -p 'msft' ssh -o StrictHostKeyChecking=no root@{} 'journalctl -a' > /opt/logs/{}/journalctl.log".format(ip, sn)
        self.get_cmd_req('ssh-keygen -R {}'.format(ip))
        self.get_cmd_req(cmd)
        #print(ping_req)
        #ping_req = self.get_bash_request('ping -n -c2 -w5 {}'.format(IP))
        #ping_req = os.popen('ping -n -c2 -w5 {}'.format(IP)).read().strip()
        match = re.search(r'2 packets transmitted, 2 received', ping_req)
        if match:
            print('------- PING [{}], SYS_SN: [{}] PASS\n'.format(ip, sn))
            status_path = os.path.join(os.path.dirname(path), '{}.status'.format(sn))
            status_api_url = 'https://{}:5003/mdaas/status'.format(ip)
            result = self._get_mdaas_data(status_api_url)
            #self.get_cmd_req('echo "{}" > {}'.format('{}'.format(result), status_path))
            if not result:
                print('======= NOT GET RESULT FROM "{}"'.format(status_api_url))
                #os.remove(path)
                return False
            with open(status_path, 'w+') as fp:
                #fp.write(str(result))
                fp.write(json.dumps(result, sort_keys=True, indent=4))
                fp.close()

            json_result=None
            historys=None
            error_list={}
            with open(status_path, 'r') as f:
                json_result = json.load(f)
                #print(repr(json_result), type(json_result))
                historys = json_result.get('history', [])
                self.err_flag=None
                for idx, history in enumerate(historys):
                    if history.get("err_code") != "None" or history.get("err_msg") != "None":
                        self.err_flag=True
                        error_list.update({'{}'.format(history.get("desc")): '{}:{}'.format(history.get("err_code"), history.get("err_msg"))})
            mdaas_mode=None if not json_result.get('detail', None) else json_result.get('detail', None).get('mdaas_mode', None)
            test_result=json_result.get('test_result', None)
            if not mdaas_mode:
                print('======= NOT FIND mdaas_mode, mdaas_mode={}'.format(mdaas_mode))
                return False
            if not test_result:
                print('======= NOT FIND test_result, test_result={}'.format(test_result))
                return False

            #MD_peq = self.get_cmd_req('grep -i "mdaas_mode.:.*intelshc" {}'.format(status_path))
            #M1_peq = self.get_cmd_req('grep -i "mdaas_mode.:.*bsl" {}'.format(status_path))
            #print(act, MD_peq, M1_peq)
            SHC_mdaas_mode_list=['intelshc', 'intelshc_1hr']
            L10_mdaas_mode_list=['bsl', 'mfg_l10_offline_a']
            if (act and mdaas_mode not in L10_mdaas_mode_list) or (not act and mdaas_mode not in SHC_mdaas_mode_list):
                print('======= INCORRECT STAGE ITEM: (MD: mdaas_mode: intelshc, M1: mdaas_mode: bsl / mfg_l10_offline_a)')
                print('{}\n'.format(result))
                self._post_mdaas_data('http://127.0.0.1:9796/api/v1/mdaas/sn_info', ip, sn)
                #print('======= REMOVE {}: INCORRECT STAGE'.format(path))
                return False
            #if act and not M1_peq:
            #    print('======= REMOVE {}: INCORRECT STAGE'.format(path))
            #    #os.remove(path)
            #    return False
            #if not act and not MD_peq:
            #    print('======= REMOVE {}: INCORRECT STAGE'.format(path))
            #    #os.remove(path)
            #    return False

            #req = self.get_cmd_req('grep -i "test_result.: .passed" {}'.format(status_path))
            #req_fail = self.get_cmd_req('grep -i "test_result.: .failed" {}'.format(status_path))
            if test_result=='passed' and not self.err_flag:
                self.pass_cnt += 1
            elif test_result=='passed' and mdaas_mode == 'bsl':
                self.pass_cnt += 1
            elif test_result=='passed' and mdaas_mode == 'mfg_l10_offline_a' and 'MST_DIMM_ERR' not in error_list.keys():
                unit_error_list_path='/home/Zane/unit_error_list/{}.txt'.format(sn)
                req=json.dumps(error_list, sort_keys=True, indent=4)+'\t\n'
                with open(unit_error_list_path, 'w+') as fp:
                    fp.write(req)
                    fp.close()
                self.pass_cnt += 1
            #elif test_result=='failed' and mdaas_mode == 'intelshc' and 'SHC test failed' in str(historys):
            #    self.pass_cnt += 1

            post_result = self._post_mdaas_data('http://127.0.0.1:9796/api/v1/mdaas/sn_info', ip, sn)
            if not post_result:
                return False

            if test_result=='failed':
                print('======= ID: [{}] SN:[{}] IP:[{}] test fail'.format(Id, sn, ip))
                self.mod_UUT_stat(sn, 'Fail')
                #print('======= REMOVE {}'.format(path))
                #os.remove(path)
                #return False

            return True
        else:
            print('------- PING [{}], SYS_SN: [{}] FAIL\n'.format(ip, sn))
            print('------- SYS IP Disconnect: RK-{} show Timeout'.format(Id))
            #self.mod_UUT_stat(sn, 'Timeout')
            print('======= MAYBE NEED to REMOVE {}'.format(path))
            #os.remove(path)
            return False

    def create_links(self, sys_info, act=True):
        net_lib = network_lib()

        print("------- RUN create_links(sys_info, act={})".format(act))
        #print(sys_info, act)
        rk_sn= sys_info.get('SN', None)
        for k,v in sys_info['UUT'].items():
            sys_sn = v.get('SN', None)
            sys_id = v.get('ID', None)
            sys_mac = v.get('MAC', None)
            if not sys_mac:
                #os.remove(path)
                raise SystemExit('======= SYS_MAC GET FAIL: rk_sn={}, sys_sn:{}'.format(rk_sn, sys_sn))
                print("======= not match r'Mac Address: (.*)\\n'", path)
            else:
                mac = sys_mac.replace(':', '-')
                dst = os.path.join(self.tftp_path, "grub.cfg-01-{}".format(mac))
                if act:
                    if not os.path.isfile(dst):
                        print("create {}".format(dst))
                        cmd = "ln -s {} {}".format("grub.cfg-L10", dst)
                        os.system(cmd)
                else:
                    if os.path.isfile(dst):
                        print("remove {}".format(dst))
                        cmd = "rm {}".format(dst)
                        os.system(cmd)
            if sys_id:
                #print(match.group(1), type(match.group(1)))
                path = os.path.join(self.dir_path, rk_sn, 'sys_info-{}.txt'.format(sys_id))
                # Check UUT alived
                if not self.check_UUT_alived(v, path, act):
                    print('{} not alived'.format(v['SN']))
                    continue
            else:
                print("======= not match r'(\d+)-\d'")

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
            #print('-------- GET UPN: {}'.format(UPN))
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
                EX_CPN_Line.extend(re.findall('CPN.*:.*{}'.format(i), req))
                #print(EX_CPN_Line)
        else:
            EX_CPN_Line = re.findall('CPN.*:.*{}'.format(EX_CPN), req)
            #print(len(EX_CPN_Line), EX_CPN_Line, UPN)
        print('-------- EX_CPN: {}'.format(EX_CPN))

        total_unit = len(EX_CPN_Line)
        print('-------- Total units: {}'.format(total_unit))
        if total_unit < 1:
            print('-------- TOTAL_UNIT of UPN NOT FIND IN {}'.format(usn_info_path))
            del self.rack_maps[rk_idx]
            return False
        self.rack_maps[rk_idx].update({'TOTAL_UNIT': total_unit})

        return True

    def check_RK_stage(self, sn, *args, **kwargs):
        rk_idx = kwargs['rk_index']

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
            print("Could not open/read file:", path)

        # check rk stage
        regex = re.compile(r'Next Process Stage:(.*)')
        match = re.search(regex, req)
        if match:
            stage = match.group(1).strip()
            if stage == 'MD':
                req = self.get_cmd_req('python3 {} -s {}'.format(self.chkroute_py, rk_sn))
                regex = re.compile(r"CheckRouteResult.*:.*OK'")
                if re.search(regex, req):
                    print('-------- CheckRouteResult: OK (rack at MD stage)')
                    self.rack_maps[rk_idx].update({'STAGE': stage})
                else:
                    print('-------- FAIL TO CheckRouteResult: Please check CheckRouteResult for MD stage')
                    del self.rack_maps[rk_idx]
                    return False
            elif stage == 'M1':
                self.rack_maps[rk_idx].update({'STAGE': stage})
            elif stage == 'WB':
                self.rack_maps[rk_idx].update({'STAGE': stage})
                print('-------- {} SN:{} at [{}] STAGE\n'.format(k, rk_sn, stage))
                del self.rack_maps[rk_idx]
                #rk_sn_path = os.path.join(tools.dir_path, rk_sn)
                if os.path.exists(rk_sn_path):
                    try:
                        shutil.rmtree(rk_sn_path)
                    except OSError as e:
                        print("Error: %s - %s." % (e.filename, e.strerror))
                return False
            else:
                print('-------- {} {} not at MD/M1 stage, stage at [{}]\n'.format(k, rk_sn, match.group(1)))
                del self.rack_maps[rk_idx]
                return False
            UPN = self.rack_maps[rk_idx]['UPN']
            print('-------- {} {} at [{}] stage [UPN: {}]\n'.format(rk_idx, rk_sn, match.group(1), UPN))
        else:
            print('-------- NOT FOUND "Next Process Stage" NOT IN {}'.format(usn_info_path))
            del self.rack_maps[rk_idx]
            return False

        return True

    def check_rk_alived(self, sn, *args, **kwargs):
        rk_sn = sn
        rk_idx = kwargs['rk_index']
        net_lib = network_lib()

        # get USN Genealogy
        rk_sn_path = os.path.join(tools.dir_path, rk_sn)
        if not os.path.exists(rk_sn_path):
            os.makedirs(rk_sn_path)
            os.chown(rk_sn_path, 1001, 1009)

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
        regex = re.compile(r"CSN.*'(.*)',.*CPN.*RACK MANAGER MAC 1")
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
            os.chown(rk_sn_path, 1001, 1009)

        # rack layout prepare
        src_path = os.path.join(tools.mdaas_dir_path, 'rack_layout.json')
        rk_layout_path = os.path.join(tools.dir_path, 'rack_layout.json')
        if not os.path.exists(rk_layout_path):
            print('move latout to {}'.format(rk_layout_path))
            if os.path.exists(src_path):
                shutil.copy(src_path, rk_layout_path)
                os.chown(rk_layout_path, 1001, 1009)
            else:
                print('Please check default rack_layout.json exist')
                exit()

        print('======== START CHECK RACK INFO {} SN:{} IP:{}'.format(k, rk_sn, rk_ip))
        # get RK info (UPN, TOTAL_UNIT, STAGE)
        if not tools.get_RK_GLB(rk_sn, rk_index=k):
            continue
        if not tools.check_RK_stage(rk_sn, rk_index=k):
            continue

        rk_upn = tools.rack_maps[k]['UPN']
        exp_sys_count = tools.rack_maps[k]['TOTAL_UNIT']
        rk_stage = tools.rack_maps[k]['STAGE']
        rk_conn_tools = RM_connecter(rk_ip)
        rk_conn = rk_conn_tools.RK_conn
        #print(rk_ip, rk_upn, exp_sys_count, rk_stage)

        # set unit range
        unit_region = list(range(3,20))+list(range(27,44))

        # update sys_info-*.txt
        sys_file_count = int(tools.get_cmd_req('ls {}/sys_info-* -l | wc -l'.format(rk_sn_path)))
        print("-------- There are {} file in {}".format(sys_file_count, rk_sn_path))
        if sys_file_count != exp_sys_count:
            tools.get_cmd_req('ssh-keygen -R {}'.format(rk_ip))
            db_insert_range = list()

            for i in unit_region:
                sys_file_path = os.path.join(rk_sn_path, 'sys_info-{}.txt'.format(i))
                if not os.path.exists(sys_file_path):
                    command='show system info -i {}'.format(i)
                    rk_conn.sendline(command)
                    index = rk_conn.expect(['WcsCli#', pexpect.TIMEOUT])
                    req = None
                    if index == 0:
                        req = rk_conn.before.decode()
                        time.sleep(1)
                    elif index == 1:
                        print('pexpect.TIMEOUT: show system info -i {}'.format(i))
                        #rk_conn.close()

                    # check need to re-config if model = C2080
                    match = re.search(r'Model: (.*)\r', req)
                    model = match.group(1) if match else None
                    if model == 'C2080':
                        soc_ip=None
                        command='set system cmd -i{} -c fru print {}'.format(i, 1)
                        rk_conn.sendline(command)
                        index = rk_conn.expect(['WcsCli#', pexpect.TIMEOUT])
                        if index == 0:
                            req_CP = rk_conn.before.decode()
                            time.sleep(1)
                        elif index == 1:
                            print('pexpect.TIMEOUT: set system cmd -i{} -c fru print {}'.format(i, 1))
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
                            req += "soc_ip: {}\n".format(soc_ip)
                        else:
                            print(repr(req_CP))

                        if soc_ip:
                            tools.get_cmd_req('ssh-keygen -R {}'.format(soc_ip))
                            cmd="sshpass -p overlake ssh -o StrictHostKeyChecking=no ovl@{} 'ls -a'".format(soc_ip)
                            tools.get_cmd_req(cmd)

                            cmd="sshpass -p overlake scp /opt/wiwynn/mdaas/client/Auto_reconfig/Script/* ovl@{}:~/".format(soc_ip)
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

                    match = re.search(r'Completion Code: (.*)\r', req)
                    if match and match.group(1) == 'Success':
                        # AC Cycle sys if file not exist
                        print('------- DC Cycle sys_info-{}'.format(i))
                        command='set system cmd -i {} -c power cycle'.format(i)
                        rk_conn.sendline(command)
                        index2 = rk_conn.expect(['WcsCli#', pexpect.TIMEOUT])
                        if index2 == 0:
                            print(rk_conn.before.decode())
                            time.sleep(3)
                        elif index2 == 1:
                            print('pexpect.TIMEOUT: {}'.format(command))
                            #rk_conn.close()

                        # Save current sys info
                        print('------- Save current sys info {}'.format(sys_file_path))
                        with open(sys_file_path, 'w+') as fp:
                            fp.write(req)
                            fp.close()
                        db_insert_range.append(i)
                    else:
                        print('------- show system info -i {}: {}'.format(i, match.group(0)))
                        status_desc = re.search(r'Status Description: (.*)\r', req)
                        if status_desc:
                            print('------- {}'.format(status_desc.group()))
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
                sys_id =  None
                sys_mac = None
                sys_sn = None
                sys_ip = None

                if not os.path.exists(path):
                    sys_id = i
                    sys_sn = '{}_CHK_RM_CONNECT'.format(i)
                    continue
                else:
                    output = None
                    try:
                        with open(path, 'r') as fp:
                            output = fp.read()
                            fp.close()

                        regex = re.compile(r"(?i)(?s)Id: (\d+)\n.*Mac Address: (\S+)\n.*SerialNumber: (\w+)\n")
                        match = re.search(regex, output)
                        if not match:
                            os.remove(path)
                            continue
                        sys_id = int(match.group(1)) if match and int(match.group(1)) == i else match
                        mac = match.group(2)
                        sys_mac = net_lib.EUI_mac(mac, formatting=mac_unix_expanded)
                        if not sys_mac:
                            os.remove(path)
                            continue
                            #raise ValidationError("Please specify a valid MAC address.")
                        sys_sn = match.group(3) if match else match
                        sys_ip = net_lib.get_ip_from_leases(sys_mac)
                        if sys_ip:
                            tools.rack_maps[k]['UUT']['{}-1'.format(i)]={'ID': sys_id, 'SN': sys_sn, 'MAC': sys_mac, 'IP': sys_ip}
                        else:
                            print('======== ip = {}, ID:{} SN:{} not find ip from test server'.format(sys_ip, sys_id, sys_sn))
                            continue

                        match = re.search(r'soc_ip: (.*)\n', output)
                        if match:
                            soc_ip=match.group(1)
                            tools.rack_maps[k]['UUT']['{}-1'.format(i)]['SOC_IP'] = soc_ip
                        else:
                            tools.rack_maps[k]['UUT']['{}-1'.format(i)]['SOC_IP'] = None
                    except OSError:
                        print("Could not open/read file:", path)
                        exit()
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
                #print(path)
                output = None
                if not os.path.isfile(path):
                    continue
                try:
                    with open(path, 'r') as fp:
                        output = fp.read()
                        fp.close()

                    regex = re.compile(r"(?i)(?s)Id: (\d+)\n.*Mac Address: (\S+)\n.*SerialNumber: (\w+)\n")
                    match = re.search(regex, output)
                    sys_id = int(match.group(1)) if match and int(match.group(1)) == i else match
                    mac = match.group(2)
                    sys_mac = net_lib.EUI_mac(mac, formatting=mac_unix_expanded)
                    if not sys_mac:
                        os.remove(path)
                        continue
                    sys_sn = match.group(3) if match else match
                    sys_ip = network_lib().get_ip_from_leases(sys_mac)
                    #print(sys_id, sys_mac, sys_sn, sys_ip)
                    sys_key = '{}-1'.format(i)
                    if sys_ip:
                        tools.rack_maps[k]['UUT'][sys_key]={'ID': sys_id, 'SN': sys_sn, 'MAC': sys_mac, 'IP': sys_ip}
                    else:
                        print('======== ip = {}, ID:{} SN:{} not find ip from test server'.format(sys_ip, sys_id, sys_sn))
                        print('======== Remove dict key')
                        if sys_key in tools.rack_maps[k]['UUT']: del tools.rack_maps[k]['UUT'][sys_key]
                        continue
                        #exit()
                    match = re.search(r'soc_ip: (.*)\n', output)
                    if match:
                        print(match)
                        soc_ip=match.group(1)
                        tools.rack_maps[k]['UUT']['{}-1'.format(i)]['SOC_IP'] = soc_ip
                    else:
                        tools.rack_maps[k]['UUT']['{}-1'.format(i)]['SOC_IP'] = None
                except OSError:
                    print("Could not open/read file:", path)
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

        # make soft link if rk_stage = M1
        rk_conn_tools.close()

    print(json.dumps(tools.rack_maps, sort_keys=True, indent=4))
    #os.system("echo '{}' > {}".format(json.dumps(tools.rack_maps, sort_keys=True, indent=4), tools.rack_maps_path))
    os.system("echo '{}' > {}".format(json.dumps(tools.rack_maps, sort_keys=True, indent=4), '/opt/logs/rack_maps.txt'))
    print(tools.rack_maps.keys())

    # START MONITIOR
    for k,v in tools.rack_maps.items():
        tools.pass_cnt = 0
        rk_sn = v['SN']
        e_pass_cnt = tools.rack_maps[k].get('TOTAL_UNIT', None)
        #tools.check_RK_stage(rk_sn, rk_index=k)
        stage = tools.rack_maps[k].get('STAGE', None)
        if stage == 'M1':
            tools.create_links(v)
        else:
            # check links is created and remove links
            tools.create_links(v, False)

        # ====== to do set_node_info_sh function: export $SN.status & update sys ip, sn to mdaas & check PASS_CNT
        req = tools.get_cmd_req('python3 {} -s {}'.format(tools.chkroute_py, rk_sn))
        regex = re.compile(r"CheckRouteResult.*:.*OK'")
        match = re.search(regex, req)
        print('CheckRouteResult for MD chcek: {}'.format(match))
        print('====================')
        print('RK SN: {}'.format(rk_sn))
        print('exc pass cnt = {}'.format(e_pass_cnt))
        print('cur pass cnt = {}'.format(tools.pass_cnt))
        if tools.pass_cnt == e_pass_cnt:# and match
        #if True:
            # get current stage
            tools.check_RK_stage(rk_sn, rk_index=k)
            stage = tools.rack_maps[k].get('STAGE', None)
            if stage:
                print('======= CHECK RK STAGE: [{}]'.format(stage))
            else:
                print('======= FAIL to CHECK RK STAGE: [{}]'.format(stage))
                exit()

            # download zip to /opt/logs/
            for x,y in v['UUT'].items():
                print(x, y)
                timestamp = tools.get_cmd_req('date +%s')
                path = "/opt/logs/{SN}-{STAGE}-{T}.zip".format(SN=y['SN'], STAGE=stage, T=timestamp)
                print('======= Download test log: {}'.format(path))
                tools.get_cmd_req('curl -X POST "http://127.0.0.1:9796/api/v1/mdaas/download" -H "accept: application/json" -H "Content-Type: application/json" -d \'{{"ip": "{}", "sn":"{}"}}\' -o {}'.format(y['IP'], y['SN'], path))
                # upload USN info
                req = tools.get_cmd_req('python3 {} -s {} -t {}'.format(tools.uploadUSNInfo_py, y['SN'], stage))
                regex = re.compile(r"UploadUSNInfoWithUniqueCheckFlagResult.*:.*OK'")
                match = re.search(regex, req)
                if not match:
                    print('------- FAIL to upload USN info [{}, {}]'.format(y['SN'], stage))
                # remove Auto reconfig file
                if stage == 'M1' and y.get('SOC_IP', None):
                    soc_ip=y['SOC_IP']
                    cmd="shpass -p overlake ssh -o StrictHostKeyChecking=no ovl@{} 'rm CP_autoReconfig.sh /vol/data/persistent/tests/fpga.py /vol/data/persistent/tests/systemd/SoCFPGATestSvc.service'".format(soc_ip)
                    print(cmd)
                    r=tools.get_cmd_req(cmd)
                    print(r)

            rk_sn_path = os.path.join(tools.dir_path, rk_sn)
            if stage == 'MD':
                req = tools.get_cmd_req('python3 {} -s {}'.format(tools.complete_py, rk_sn))
                regex = re.compile(r"CompleteResult.*:.*OK'")
                match = re.search(regex, req)
                if match:
                    tools.check_RK_stage(rk_sn, rk_index=k)
                    n_stage = tools.rack_maps[k].get('STAGE', None)
                    if n_stage != 'MD':
                        print('{} {} move {} to {} stage'.format(k, rk_sn, stage, n_stage))
                    else:
                        print('FAIL to move stage {} to M1'.format(stage))
                    if os.path.exists(rk_sn_path):# and n_stage == 'M1':
                        tools.create_links(v)
                        try:
                            shutil.rmtree(rk_sn_path)
                        except OSError as e:
                            print("Error: %s - %s." % (e.filename, e.strerror))
                else:
                    print('FAIL for move MD to M1')
                    print('{} {} at {} stage'.format(k, rk_sn, stage))
                    exit()
            elif stage == 'M1':
                tools.create_links(v, False)
                req = tools.get_cmd_req('python3 {} -s {} -t M1'.format(tools.complete_py, rk_sn))
                regex = re.compile(r"CompleteResult.*:.*OK'")
                match = re.search(regex, req)
                if match:
                    print(match.group())
                    #tools.check_RK_stage(rk_sn, rk_index=k)
                    #n_stage = tools.rack_maps[k].get('STAGE', None)
                    n_stage = 'WB'
                    print('======= {} move {} stage to {}'.format(k, stage, n_stage))
                    print(rk_sn_path)
                    if os.path.exists(rk_sn_path):
                        try:
                            shutil.rmtree(rk_sn_path)
                        except OSError as e:
                            print("Error: %s - %s." % (e.filename, e.strerror))
                else:
                    print('======= FAIL to move {} stage WB '.format(stage))
                    print('{} {} at {} stage'.format(k, rk_sn, stage))
                    print(req)
                    exit()
            elif stage == 'WD':
                print('======= RK at WD already')
                continue
        else:
            pass
