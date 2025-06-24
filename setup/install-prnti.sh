set -e
name=$(basename $(git rev-parse --show-toplevel))

echo "~~~ install service ~~~~"
sudo cp -f setup/$name.service /lib/systemd/system/$name.service
sudo chmod 644 /lib/systemd/system/$name.service
sudo systemctl daemon-reload
sudo systemctl enable $name.service
sudo service $name start

echo "~~~ install pip requirements ~~~~"
source .venv/bin/activate
python3 -m pip install -r requirements.txt
