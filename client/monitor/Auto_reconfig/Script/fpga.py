import os
import sys

def main(argv):

 os.system("modprobe catapult")
 os.system("fpgadiagnostics -dumphealth")
 os.system("fpgadiagnostics -reconfigapp")
 os.system("fpgadiagnostics -dumphealth")
 os.system("Fpgafactorytester -stress 3")

#Skip blow cmd to keep auto-reconfig while system AC or DC
# os.system("rm /vol/data/persistent/tests/systemd/SoCFPGATestSvc.service")

 sys.exit(0)

if __name__ == "__main__":
 main(sys.argv[1:])
