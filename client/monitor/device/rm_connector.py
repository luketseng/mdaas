import pexpect

from lib.log import log

SERVER = {
    'port': '22',
    'username': 'root',
    'password': '$pl3nd1D',
}

SSH_EXPECT_LIST = [
    'yes/no',
    'password:',
    'WcsCli#',
    pexpect.EOF,
    pexpect.TIMEOUT,
]

PW_EXPECT_LIST = [
    'password:',
    pexpect.EOF,
    pexpect.TIMEOUT,
]

RM_EXPECT_LIST = [
    'WcsCli#',
    pexpect.EOF,
    pexpect.TIMEOUT,
]

BMC_EXPECT_LIST = [
    'root@localhost:~#',
    pexpect.EOF,
    pexpect.TIMEOUT
]


class RmConnecter(object):
    RK_conn = None

    def __init__(self, ip, *args, **kwargs):
        server = SERVER
        server["hostname"] = ip
        self._ssh_rm(server)

    def _ssh_rm(self, server):
        command = 'ssh -p %s %s@%s' % (server['port'],
                                       server['username'], server['hostname'])
        process = pexpect.spawn(command, timeout=30)
        ssh_expect_list = SSH_EXPECT_LIST
        index = process.expect(ssh_expect_list)
        if index == 0:  # ssh success with confirmation
            process.sendline("yes")
            expect_list = PW_EXPECT_LIST
            index = process.expect(expect_list)
            if index == 0:
                self._to_rm(process, server)
            else:
                log('EOF or TIMEOUT')
                process.close()
        elif index == 1:  # ssh success without confirmation
            self._to_rm(process, server)
        else:
            log('EOF or TIMEOUT')
            process.close()
        self.RK_conn = process

    def _to_rm(self, process, server):
        process.sendline(server['password'])
        rm_expect_list = RM_EXPECT_LIST
        index = process.expect(rm_expect_list)
        if index == 0:
            log('{} connect success\n'.format(server["hostname"]))

    def CP_sendline(self, command):
        timeout = 30
        prompt = BMC_EXPECT_LIST
        log('------- Send CP command [{}]'.format(repr(command)))
        self.RK_conn.sendcontrol('c')
        self.RK_conn.expect(prompt)
        self.RK_conn.sendline(command)
        index = self.RK_conn.expect(prompt, timeout=timeout)
        if index == 0:
            req = self.RK_conn.before.decode()
            log(repr(req))
            return req
        else:
            log('pexpect.TIMEOUT: {}'.format(command))
            return False

    def close(self):
        log('Run self.RK_conn.close()', self.RK_conn.args)
        self.RK_conn.close()


if __name__ == '__main__':
    testing_ip = '192.168.8.20'
    rm = RmConnecter(testing_ip)
