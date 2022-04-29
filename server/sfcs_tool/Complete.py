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

def Complete(sn, stage=DEFAULT_SFCS_STAGE, ip=DEFAULT_SFCS_IP, operator=DEFAULT_SFCS_OPERATOR, pass_fail=1):
    SFCS = SFCS_API(ip)
    #SFCS.FetchMethodList()

    method = 'Complete'
    insert = SFCS.Action(method)
    insert[method]['UnitSerialNumber'] = sn
    insert[method]['StageCode'] = stage
    insert[method]['EmployeeID'] = operator
    insert[method]['Line'] = 'MD'
    insert[method]['StationName'] = 'MD'
    insert[method]['Pass'] = pass_fail
    print(insert)
    print('Method: {}'.format(method))
    CompleteRes = SFCS.Action(method, insert)
    res = CompleteRes
    
    return res


# End Sub-function ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--IP", help="SFCS IP", default=DEFAULT_SFCS_IP)
    parser.add_argument("-s", "--USN", help="Unit Serial Number")
    parser.add_argument("-t", "--Stage", help="Stage", default=DEFAULT_SFCS_STAGE)
    parser.add_argument("-o", "--Operator", help="Operator", default=DEFAULT_SFCS_OPERATOR)
    args = parser.parse_args()

    res = Complete(ip=args.IP, sn=args.USN, stage=args.Stage, operator=args.Operator)
    print(res)

    return 0


if __name__ == '__main__':
    main()


exit()

