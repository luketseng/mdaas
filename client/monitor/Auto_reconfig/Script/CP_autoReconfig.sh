mkdir /vol/data/persistent/tests
sleep 2
chmod 777 /vol/data/persistent/tests
sleep 2
mkdir /vol/data/persistent/tests/systemd
sleep 2
chmod 777 /vol/data/persistent/tests/systemd
sleep 2
mv /home/ovl/SoCFPGATestSvc.service /vol/data/persistent/tests/systemd
sleep 5
chmod 777 /vol/data/persistent/tests/systemd/SoCFPGATestSvc.service
sleep 2
mv /home/ovl/fpga.py /vol/data/persistent/tests/
sleep 5
chmod 777 /vol/data/persistent/tests/fpga.py
sleep 10
ls /vol/data/persistent/tests/systemd/SoCFPGATestSvc.service /vol/data/persistent/tests/fpga.py -al
reboot
