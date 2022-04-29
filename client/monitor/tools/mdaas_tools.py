import subprocess
import os, sys
import re
import time
import requests
import json
import shutil
from netaddr import mac_unix_expanded
import pexpect

from device.rm_connector import RmConnecter

IPXE_TAG = "MDAAS_IMG_TYPE"
IMG_TYPE_MAP = {"MD": "linux_shc", "M1C": "linux_golden_conf", "M1": "linux_l10", "WIN": "winpe"}

class Tools(object):
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
        process = os.popen(cmd)
        req = process.read().strip()
        process.close()

        return req

    def get_bash_request(self, cmd):
        cmd = cmd.split(' ')
        print(cmd)
        try:
            out = subprocess.check_output(cmd,
                stderr=subprocess.STDOUT
                )
            stdout,stderr = out.communicate(timeout=10)
        except subprocess.CalledProcessError as e:
            return False

        return True

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
            result = response.json()
            return result
        except requests.exceptions.RequestException as e:
            return None


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

            result = response.json()
            return result
        except requests.exceptions.RequestException as e:
            # catastrophic error. bail.
            raise SystemExit(e)


    def check_UUT_alived(self, sys_info, path, act):
        sn = sys_info['SN']

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
        match = re.search(r'2 packets transmitted, 2 received', ping_req)
        if match:
            print('------- PING [{}], SYS_SN: [{}] PASS\n'.format(ip, sn))
            status_path = os.path.join(os.path.dirname(path), '{}.status'.format(sn))
            status_api_url = 'https://{}:5003/mdaas/status'.format(ip)
            result = self._get_mdaas_data(status_api_url)
            if not result:
                print('======= NOT GET RESULT FROM "{}"'.format(status_api_url))
                return False
            with open(status_path, 'w+') as fp:
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

            SHC_mdaas_mode_list=['intelshc', 'intelshc_1hr']
            L10_mdaas_mode_list=['bsl', 'mfg_l10_offline_a']
            if (act and mdaas_mode not in L10_mdaas_mode_list) or (not act and mdaas_mode not in SHC_mdaas_mode_list):
                print('======= INCORRECT STAGE ITEM: (MD: mdaas_mode: intelshc, M1: mdaas_mode: bsl / mfg_l10_offline_a)')
                print('{}\n'.format(result))
                self._post_mdaas_data('http://127.0.0.1:9796/api/v1/mdaas/sn_info', ip, sn)
                return False

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


            return True
        else:
            print('------- PING [{}], SYS_SN: [{}] FAIL\n'.format(ip, sn))
            print('------- SYS IP Disconnect: RK-{} show Timeout'.format(Id))
            #self.mod_UUT_stat(sn, 'Timeout')
            print('======= MAYBE NEED to REMOVE {}'.format(path))
            #os.remove(path)
            return False

    def create_ipxe_menu(self, sys_info, stage, golden_cfg=False):
        # create format f4-6b-8c-6e-a2-e7_menu.ipxe from base_menu.ipxe

        img_type = IMG_TYPE_MAP.get('M1C') if golden_cfg else IMG_TYPE_MAP.get(stage)

        rk_sn= sys_info.get('SN', None)
        for v in sys_info['UUT'].values():
            sys_sn =  v.get('SN', None)
            sys_id = v.get('ID', None)
            sys_mac = v.get('MAC', None)
            if not sys_mac:
                raise SystemExit('======= SYS_MAC GET FAIL: rk_sn={}, sys_sn:{}'.format(rk_sn, sys_sn))
            mac = sys_mac.replace(':', '-')
            src = os.path.join(self.tftp_path, "ipxe_mac_menu", "base_menu.ipxe")
            dst = os.path.join(self.tftp_path, "ipxe_mac_menu", "{}_menu.ipxe".format(mac))
            if not os.path.isfile(dst):
                print("create {}".format(dst))
                fin = open(src, "rt")
                fout = open(dst, "wt")
                [ fout.write(line.replace(IPXE_TAG, img_type)) for line in fin ]
            if not sys_id:
                print("======= not match r'(\d+)-\d'")
                return
            path = os.path.join(self.dir_path, rk_sn, 'sys_info-{}.txt'.format(sys_id))
            # Check UUT alived
            act = True if stage == 'M1' else False
            if not self.check_UUT_alived(v, path, act):
                print('{} not alived'.format(v['SN']))
                continue

    def create_links(self, sys_info, act=True):

        print("------- RUN create_links(sys_info, act={})".format(act))
        #print(sys_info, act)
        rk_sn= sys_info.get('SN', None)
        for k,v in sys_info['UUT'].items():
            sys_sn = v.get('SN', None)
            sys_id = v.get('ID', None)
            sys_mac = v.get('MAC', None)
            if not sys_mac:

                raise SystemExit('======= SYS_MAC GET FAIL: rk_sn={}, sys_sn:{}'.format(rk_sn, sys_sn))
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
                path = os.path.join(self.dir_path, rk_sn, 'sys_info-{}.txt'.format(sys_id))
                # Check UUT alived
                if not self.check_UUT_alived(v, path, act):
                    print('{} not alived'.format(v['SN']))
                    continue
            else:
                print("======= not match r'(\d+)-\d'")

    def get_RK_GLB(self, sn, rk_sn, *args, **kwargs):
        # change argument add rk_sn
        rk_idx = kwargs['rk_index']
        encoding = 'utf-8'

        # get USN Genealogy
        rk_sn_path = os.path.join(self.dir_path, rk_sn)
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
        rk_layout_path = os.path.join(self.dir_path, 'rack_layout.json')
        if not os.path.exists(rk_layout_path):
            print('Please check rack_layout.json exist in {}'.format(self.dir_path))
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

    def check_RK_stage(self, sn, rk_sn, *args, **kwargs):
        # change argument add rk_sn
        rk_idx = kwargs['rk_index']

        # get USN Genealogy
        rk_sn_path = os.path.join(self.dir_path, rk_sn)
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
                print('-------- {} SN:{} at [{}] STAGE\n'.format(rk_idx, rk_sn, stage))
                del self.rack_maps[rk_idx]
                #rk_sn_path = os.path.join(tools.dir_path, rk_sn)
                if os.path.exists(rk_sn_path):
                    try:
                        shutil.rmtree(rk_sn_path)
                    except OSError as e:
                        print("Error: %s - %s." % (e.filename, e.strerror))
                return False
            else:
                print('-------- {} {} not at MD/M1 stage, stage at [{}]\n'.format(rk_idx, rk_sn, match.group(1)))
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
        from lib.network import Network
        rk_sn = sn
        rk_idx = kwargs['rk_index']
        net_lib = Network()

        # get USN Genealogy
        rk_sn_path = os.path.join(self.dir_path, rk_sn)
        if not os.path.exists(rk_sn_path):
            os.makedirs(rk_sn_path)
            os.chown(rk_sn_path, 1001, 1009)

        usn_info_path = os.path.join(rk_sn_path, 'usn_info-{}.txt'.format(sn))

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
                    print('-------- {} IP Disconnect: SET U27 Disconnect'.format(rk_idx))
                    UUT_SN = self.rack_maps[rk_idx]['UUT']['27-1']['SN']
                    self.mod_UUT_stat(self.rack_maps[rk_idx]['UUT']['27-1']['SN'], 'Disconnect')
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

    def re_config_CP(self, rk_ip, index):
        # change first argument to rk_ip
        i=index
        print('======== Run re-config function')
        rk_conn_tools_CP = RmConnecter(rk_ip)
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


if __name__ == '__main__':
    tools = Tools()
    result = tools.get_cmd_req('python3 --version')
    print(result)

    from lib.SQL import SQL
    sql = SQL()
    req = sql.select_rk_nd_info('')
    tools.parser_db_sys_info(req)

    result = tools.check_rk_alived('R286820240011012', rk_index='RK-02')

    sys_info = {'SN': 'R286820240011012', 'UUT': {'_': {'SN': 'P286920270094012', 'ID': '123', 'MAC': '04:27:28:04:b4:e7'}}}
    stage = 'MD'
    tools.create_ipxe_menu(sys_info, stage, golden_cfg=False)