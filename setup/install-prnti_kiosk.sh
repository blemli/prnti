set -e

echo "~~~ disable prnti mail monitor ~~~"
sudo systemctl stop prnti.service 2>/dev/null || true
sudo systemctl disable prnti.service 2>/dev/null || true

echo "~~~ install kiosk service ~~~"
sudo cp -f setup/prnti_kiosk.service /lib/systemd/system/prnti_kiosk.service
sudo chmod 644 /lib/systemd/system/prnti_kiosk.service
sudo systemctl daemon-reload
sudo systemctl enable prnti_kiosk.service
sudo systemctl start prnti_kiosk.service

echo "~~~ install pip requirements ~~~"
source .venv/bin/activate
python3 -m pip install -r requirements.txt

echo "~~~ done ~~~"
echo "prnti mail monitor: disabled"
echo "prnti kiosk: enabled and started"
