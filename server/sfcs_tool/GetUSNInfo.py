#!/usr/bin/env python
import os
import argparse
import json

from sfcs_api import SFCS_API


# Sub-function ----------------------------------------------------------------
SFCS_CFG_FILE = '{}/WIWYNN_SFCS_CFG.json'.format(os.path.dirname(os.path.abspath(__file__)))
with open(SFCS_CFG_FILE, 'r') as SFCS_CFG:
    SFCS_CFG_DATA = json.load(SFCS_CFG)

DEFAULT_SFCS_IP = SFCS_CFG_DATA['IP']['WYTN']
DEFAULT_SFCS_STAGE = SFCS_CFG_DATA['Stage']['PCBA']['ICT']


def GetUSNInfo(sn, stage=DEFAULT_SFCS_STAGE, ip=DEFAULT_SFCS_IP):
    SFCS = SFCS_API(ip)
    method = 'GetUSNInfo'
    insert = SFCS.Action(method)
    insert[method]['UnitSerialNumber'] = sn
    insert[method]['StageCode'] = stage
    
    print('Method: {}'.format(method))
    USNInfo = SFCS.Action(method, insert)
    #print(USNInfo)
    
    return USNInfo
    

# End Sub-function ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--IP", help="SFCS IP", default=DEFAULT_SFCS_IP)
    parser.add_argument("-s", "--USN", help="Unit Serial Number")
    parser.add_argument("-t", "--Stage", help="Stage", default=DEFAULT_SFCS_STAGE)
    args = parser.parse_args()

    res = GetUSNInfo(ip=args.IP, sn=args.USN, stage=args.Stage)
    #print(res)
    
    print('Unit S/N:{}'.format(res['GetUSNInfoResponse']['GetUSNInfoResult']['USN']))
    print('   Model:{}'.format(res['GetUSNInfoResponse']['GetUSNInfoResult']['Model']))
    print('Unit P/N:{}'.format(res['GetUSNInfoResponse']['GetUSNInfoResult']['ProductCode']))

    return 0


if __name__ == '__main__':
    main()


exit()

