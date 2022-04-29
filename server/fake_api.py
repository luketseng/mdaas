# -*- encoding: utf8-*-

from flask import Flask, request, make_response, send_file
import flask
import json

app = Flask(__name__)

# PS1: PXE server access info: sshpass -p azuremte ssh root@10.49.30.152
# PS2: UUT access info: /opt/wiwynn# curl -k https://192.168.11.233:5003/mdaas/status
# {"status": "starting", "desc": "", "items": 0, "current": 0, "test_result": "pending", "azure_upload": "pending", "history": [], "detail": {"ntp": "failed", "azure": "unknown", "mdaas_mode": "intelshc", "test_start_time": "2021-01-25T08:24:31.572645Z"}}


@app.route("/mdaas/status", methods=['GET'])
def status():
    data = {
        "status": "finished",
        "desc": "CPU/Memory Stress Test",
        "items": 8,
        "current": 2,
        "test_result": "pending",
        "azure_upload": "pending",
        "history": [
            {
                "status": "pass",
                "desc": "Clear BMC SEL",
                "err_code": "None",
                "err_msg": "None"
            },
            {
                "status": "fail",
                "desc": "Check BMC SEL with Whitelist",
                "err_code": "BMC_CHK_SEL_ERR",
                "err_msg": "FOUND SEL error:{'xxxxxxxx'}"
            }
        ],
        "detail": {
            "ntp": "failed",
            "azure": "unknown",
            "mdaas_mode": "intelshc",
            "test_start_time": "2021-01-25T08:24:31.572645Z"
        }
    }
    return make_response(json.dumps(data), 200)


@app.route("/mdaas/log_list", methods=['GET'])
def log_list():
    data = {
        "log_options": [
            "/mdaas/log/diag",
            "/mdaas/log/api",
            "/mdaas/log/report.txt",
            "/mdaas/log/shc.log",
            "/mdaas/log/bmc_sensor_data.csv",
            "/mdaas/log/seq_state.json",
            "/mdaas/log/PPIN.txt",
            "/mdaas/log/fpga_fru.json",
            "/mdaas/log/bmc_fru_data.csv",
            "/mdaas/log/smartctl.txt",
            "/mdaas/log/bios_config.txt",
            "/mdaas/log/intelshc.xml",
            "/mdaas/log/cerberus_info.json",
            "/mdaas/log/journalctl_log.txt",
            "/mdaas/log/srv_info.csv",
            "/mdaas/log/os_info.csv",
            "/mdaas/log/nvme_list.json",
            "/mdaas/log/nvme_nvme5n1_FJ04N5827I1604D5T_smartlog.json",
            "/mdaas/log/nvme_nvme4n1_FJ04N5827I1604D5U_smartlog.json",
            "/mdaas/log/nvme_nvme3n1_FJ04N5827I1604D5R_smartlog.json",
            "/mdaas/log/nvme_nvme2n1_FJ04N5827I1604D5Q_smartlog.json",
            "/mdaas/log/nvme_nvme1n1_FJ04N5827I1604D5S_smartlog.json",
            "/mdaas/log/nvme_nvme0n1_FJ04N5827I1604D5V_smartlog.json",
            "/mdaas/log/lscpu.json",
            "/mdaas/log/bmc_selv.txt",
            "/mdaas/log/bmc_sel.txt",
            "/mdaas/log/lsblk.txt",
            "/mdaas/log/dmidecode.txt",
            "/mdaas/log/lspci_vvvxbk.txt",
            "/mdaas/log/lshw_sanitized.xml",
            "/mdaas/log/lshw_normal.xml",
            "/mdaas/log/diag.log",
            "/mdaas/log/auto_start.log",
            "/mdaas/log/network_monitor_verbose.log",
            "/mdaas/log/monitor.log",
            "/mdaas/log/api.log"
        ]
    }
    return make_response(json.dumps(data), 200)


@app.route("/mdaas/log/<target>", methods=['GET'])
def log_content(target):
    # api
    data = {
        "body": "[2021-01-25 08:23:40,761] p1683 {app.py:140} INFO - Using certificate '/etc/pki/tls/certs/mdaas_uut_api.crt' for TLS encryption\n[2021-01-25 08:23:40,764] p1683 {werkzeug/_internal.py:113} INFO -  * Running on https://0.0.0.0:5003/ (Press CTRL+C to quit)\n[2021-01-25 08:24:31,705] p1683 {endpoints/status.py:99} INFO - Status: {'status': 'starting', 'desc': '', 'items': 0, 'current': 0, 'test_result': 'pending', 'azure_upload': 'pending', 'history': '(0 items)', 'detail': {'ntp': 'failed', 'azure': 'unknown', 'mdaas_mode': 'intelshc', 'test_start_time': '2021-01-25T08:24:31.572645Z'}}\n[2021-01-25 08:24:31,706] p1683 {werkzeug/_internal.py:113} INFO - 192.168.11.1 - - [25/Jan/2021 08:24:31] \"\u001b[37mGET /mdaas/status HTTP/1.1\u001b[0m\" 200 -\n[2021-01-25 08:30:12,495] p1683 {werkzeug/_internal.py:113} INFO - 192.168.11.1 - - [25/Jan/2021 08:30:12] \"\u001b[37mGET /mdaas/log_list HTTP/1.1\u001b[0m\" 200 -\n[2021-01-25 08:32:08,066] p1683 {endpoints/log.py:55} DEBUG - Target Log: auto_start.log\n[2021-01-25 08:32:08,067] p1683 {werkzeug/_internal.py:113} INFO - 192.168.11.1 - - [25/Jan/2021 08:32:08] \"\u001b[37mGET /mdaas/log/auto_start.log HTTP/1.1\u001b[0m\" 200 -\n[2021-01-25 09:59:24,250] p1683 {endpoints/status.py:99} INFO - Status: {'status': 'crashed', 'desc': 'Intel SHC Stress', 'items': 1, 'current': 1, 'test_result': 'pending', 'azure_upload': 'failed', 'history': '(0 items)', 'detail': {'ntp': 'failed', 'azure': 'down', 'mdaas_mode': 'intelshc', 'test_start_time': '2021-01-25T08:24:31.572645Z', 'flow': '/root/xml/intelshc.xml'}}\n[2021-01-25 09:59:24,251] p1683 {werkzeug/_internal.py:113} INFO - 192.168.11.1 - - [25/Jan/2021 09:59:24] \"\u001b[37mGET /mdaas/status HTTP/1.1\u001b[0m\" 200 -\n[2021-01-25 10:00:15,256] p1683 {werkzeug/_internal.py:113} INFO - 192.168.11.1 - - [25/Jan/2021 10:00:15] \"\u001b[37mGET /mdaas/log_list HTTP/1.1\u001b[0m\" 200 -\n[2021-01-25 10:01:47,291] p1683 {endpoints/log.py:55} DEBUG - Target Log: report.txt\n[2021-01-25 10:01:47,292] p1683 {werkzeug/_internal.py:113} INFO - 192.168.11.1 - - [25/Jan/2021 10:01:47] \"\u001b[37mGET /mdaas/log/report.txt HTTP/1.1\u001b[0m\" 200 -\n[2021-01-25 10:02:08,119] p1683 {endpoints/log.py:55} DEBUG - Target Log: api\n"
    }
    return make_response(json.dumps(data), 200)


@app.route("/mdaas/flow", methods=['GET'])
def flow():
    data = {"items": [{"class": "Shc", "description": "Intel SHC Stress"}]}
    return make_response(json.dumps(data), 200)


@app.route("/mdaas/version", methods=['GET'])
def version():
    data = {
        "version": "MDaaS POC-43",
        "detail": {
            "image_version": "Mariner OS 1.0.MM4",
            "release_version": "POC-43",
            "build_date": "2020-11-23 23:44:36Z",
            "kernel_version": "4.18.0-147.el8.x86_64",
            "kernel_flags": "BOOT_IMAGE=linux/vmlinuz-4.18.0-147.el8.x86_64 ramdisk_size=4G ip=dhcp rw loglevel=3 console=ttyS0,115200 mfg_state=L10 mdaas_mode=intelshc mdaas_flags=gw-192.168.11.1,dns-192.168.255.254",
            "uut_api_version": "202011.2.3-dev.gite692b94",
            "srvdiag_version": "202011.23.3-sateeshwiwynn.gitb73535b",
            "si": "wiwynn",
            "linux_base_build_version": "202011.23.1-sateeshwiwynn.git9073f7b"
        }
    }
    return make_response(json.dumps(data), 200)


@app.route("/mdaas/blob_list", methods=['GET'])
def blob_list():
    data = {
        "blob_options": [
            "/mdaas/blob/P103104360001012_2021-01-25T08.24.31_CRASH.zip",
            "/mdaas/blob/P103104360001012_2021-01-25T08.24.31_START.zip",
            "/mdaas/blob/latest"
        ]
    }
    return make_response(json.dumps(data), 200)


@app.route("/mdaas/blob/<target>", methods=['GET'])
def blob_target(target):
    return send_file('./api_specs/MDaaS_UUT_API-20201116.pdf')


if __name__ == '__main__':
    app.run(
        host="0.0.0.0",
        port=5003,
        ssl_context='adhoc',
        threaded=True,
        debug=True
    )
