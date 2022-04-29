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
DEFAULT_SFCS_STAGE = SFCS_CFG_DATA['Stage']['PCBA']['ICT']


def FetchMethodList(ip=DEFAULT_SFCS_IP):
    SFCS = SFCS_API(ip)
    SFCS.FetchMethodList()
    #insert = SFCS.Action('GetDynamicData')
    #print(insert)
    return 0    

# End Sub-function ------------------------------------------------------------
def GetKeyByValue(dict, value):
    key_list = list(dict.keys())
    val_list = list(dict.values())
    #print(key_list)
    #print(val_list)
    return key_list[val_list.index(value)]
    

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--IP", help="SFCS IP", default=DEFAULT_SFCS_IP)
    args = parser.parse_args()

    print('SFCS IP [{}]: {}'.format(GetKeyByValue(SFCS_CFG_DATA['IP'], args.IP), args.IP))
    print('--------')
    res = FetchMethodList(ip=args.IP)

    return 0


if __name__ == '__main__':
    main()


exit()
