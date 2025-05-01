# prnti

*prnti for wnti*

<img src="prnti.svg" alt="prnti" style="zoom:25%;" />



```bash
lsusb | grep Epson
sudo touch /etc/udev/rules.d/99-escpos.rules
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="04b8", ATTRS{idProduct}=="0202", MODE="0664", GROUP="dialout"' |sudo tee -a /etc/udev/rules.d/99-escpos.rules
sudo usermod -aG dialout $USER
sudo service udev restart
sudo udevadm control --reload-rules
sudo udevadm trigger

sudo apt install python3-dev libcups2-dev -y
#sudo apt install chromium chromium-driver -y  # auf Bookworm/Bullseye

python3 -m venv .venv
source .venv/bin/activate
python3 -m ensurepip
python3 -m pip install python-escpos[all]
```

