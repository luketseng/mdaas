#!/usr/bin/env python
import os
import argparse
import json

from sfcs_api import SFCS_API


# Sub-function ----------------------------------------------------------------
SFCS_CFG_FILE = '{}/WIWYNN_SFCS_CFG.json'.format(os.path.dirname(os.path.abspath(__file__)))
with open(SFCS_CFG_FILE, 'r') as SFCS_CFG:
    SFCS_CFG_DATA = json.load(SFCS_CFG)

DEFAULT_SFCS_IP = SFCS_CFG_DATA['IP']['WMX']
DEFAULT_SFCS_STAGE = SFCS_CFG_DATA['Stage']['L11']['MDaaS']
DEFAULT_SFCS_OPERATOR= 'MDAASTEST'

def CheckRoute(sn, stage=DEFAULT_SFCS_STAGE, ip=DEFAULT_SFCS_IP):
    SFCS = SFCS_API(ip)
    #SFCS.FetchMethodList()

    method = 'CheckRoute'
    insert = SFCS.Action(method)
    insert[method]['UnitSerialNumber'] = sn
    insert[method]['StageCode'] = stage
    print(insert)
    print('Method: {}'.format(method))
    CheckRouteRes = SFCS.Action(method, insert)
    res = CheckRouteRes
    return res


# End Sub-function ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--IP", help="SFCS IP", default=DEFAULT_SFCS_IP)
    parser.add_argument("-s", "--USN", help="Unit Serial Number")
    parser.add_argument("-t", "--Stage", help="Stage", default=DEFAULT_SFCS_STAGE)
    args = parser.parse_args()

    res = CheckRoute(ip=args.IP, sn=args.USN, stage=args.Stage)
    print(res)

    return 0


if __name__ == '__main__':
    main()


exit()

