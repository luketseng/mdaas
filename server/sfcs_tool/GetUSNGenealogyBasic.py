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
DEFAULT_SFCS_STAGE = SFCS_CFG_DATA['Stage']['L11']['Pre-Run']


def GetUSNGenealogyBasic(sn, stage=DEFAULT_SFCS_STAGE, ip=DEFAULT_SFCS_IP):
    SFCS = SFCS_API(ip)
    #SFCS.FetchMethodList()

    # USNGenealogyBasic
    method = 'GetUSNGenealogyBasic'
    insert = SFCS.Action(method)
    insert[method]['UnitSerialNumber'] = sn
    insert[method]['StageCode'] = stage
    print('Method: {}'.format(method))
    USNGenealogyBasic = SFCS.Action(method, insert)
    #print(USNGenealogyBasic)
    
    Tour = USNGenealogyBasic['GetUSNGenealogyBasicResponse']['GetUSNGenealogyBasicResult']['Tour']
    Tour = ','.join(Tour[i:i+2] for i in range(0, len(Tour), 2))
    #print(Tour)

    USNGenealogyBasic['GetUSNGenealogyBasicResponse']['GetUSNGenealogyBasicResult'].update({ "Tour": Tour })
    #print(USNGenealogyBasic)
    
    res = USNGenealogyBasic
    
    return res


# End Sub-function ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--IP", help="SFCS IP", default=DEFAULT_SFCS_IP)
    parser.add_argument("-s", "--USN", help="Unit Serial Number")
    parser.add_argument("-t", "--Stage", help="Stage", default=DEFAULT_SFCS_STAGE)
    args = parser.parse_args()

    res = GetUSNGenealogyBasic(ip=args.IP, sn=args.USN, stage=args.Stage)
    #print(res)
    
    print('                Unit S/N:{}'.format(res['GetUSNGenealogyBasicResponse']['GetUSNGenealogyBasicResult']['USN']))
    print('               MO Number:{}'.format(res['GetUSNGenealogyBasicResponse']['GetUSNGenealogyBasicResult']['MO']))
    print('                Unit P/N:{}'.format(res['GetUSNGenealogyBasicResponse']['GetUSNGenealogyBasicResult']['UPN']))
    print('              Stage Tour:{}'.format(res['GetUSNGenealogyBasicResponse']['GetUSNGenealogyBasicResult']['Tour']))
    print('      Next Process Stage:{}'.format(res['GetUSNGenealogyBasicResponse']['GetUSNGenealogyBasicResult']['NextStage']))
    print('Previous Processed Stage:{}'.format(res['GetUSNGenealogyBasicResponse']['GetUSNGenealogyBasicResult']['Stage']))
    
    print(res)

    return 0


if __name__ == '__main__':
    main()


exit()

