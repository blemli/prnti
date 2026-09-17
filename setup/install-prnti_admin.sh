set -e

echo "~~~ install pip requirements ~~~"
source .venv/bin/activate
python3 -m pip install -r requirements.txt

echo "~~~ make sure playwright has its chromium (needed by get_all) ~~~"
playwright install chromium

echo "~~~ install admin service ~~~"
sudo cp -f setup/prnti_admin.service /lib/systemd/system/prnti_admin.service
sudo chmod 644 /lib/systemd/system/prnti_admin.service
sudo systemctl daemon-reload
sudo systemctl enable prnti_admin.service
sudo systemctl restart prnti_admin.service

echo "~~~ done ~~~"
echo "prnti admin: http://$(hostname).local:8080"
