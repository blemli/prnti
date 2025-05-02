NAME="offnomat"
DESCRIPTION="is it open or not?"

echo "~~~ make installation stuff executable ~~~"
sudo chmod +x setup/*.sh

echo "~~~ turn off swapping to preserve sdcards ~~~"
sudo swapoff --all                            # swapping is stupid anyways
sudo apt autoremove -y --purge dphys-swapfile # and then we dont need the swapfile anymore
#todo: noatime

echo "~~~ add convenience aliases ~~~"
echo "alias restart='sudo service $NAME restart && sudo service avahi-daemon restart'" >> ~/.bash_profile
echo "alias follow='journalctl -u $NAME --follow'" >> ~/.bash_profile
echo "alias errors='journalctl -u $NAME -b -p emerg..err'" >> ~/.bash_profile
echo "alias update='cd /opt/$NAME && setup/update.sh'" >> ~/.bash_profile
echo "alias status='service $NAME status'" >> ~/.bash_profile
echo "alias disable='sudo service $NAME stop && sudo systemctl disable $NAME'" >> ~/.bash_profile
echo "alias enable='sudo systemctl enable $NAME && sudo service start $NAME'" >> ~/.bash_profile


echo "~~~ install basic tools ~~~"
sudo apt install -y dnsutils vim git tldr python3-pip bat tmux iptables

echo "~~~install specific dependencies"
sudo touch /etc/udev/rules.d/99-escpos.rules
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="04b8", ATTRS{idProduct}=="0202", MODE="0664", GROUP="dialout"' |sudo tee -a /etc/udev/rules.d/99-escpos.rules
sudo usermod -aG dialout $USER
sudo service udev restart
sudo udevadm control --reload-rules
sudo udevadm trigger

sudo apt install python3-dev libcups2-dev -y
sudo apt install -y libgtk-4-1 libgraphene-1.0-0
#sudo apt install chromium chromium-driver -y  # auf Bookworm/Bullseye




echo "~~~ disable password login via ssh ~~~"
#todo

echo "~~~ set custom login banner ~~~"
sudo apt install -y figlet
figlet $NAME >>motd
echo "by Problemli" >>motd
echo " " >>motd
echo " >> $DESCRIPTION << " >>motd
echo " " >>motd
echo " " >>motd
echo "   restart: sudo service $NAME restart" >>motd
echo "   disable: sudo systemctl disable $NAME" >>motd
echo "   live logs: journalctl -u $NAME --follow" >>motd
echo "   errors since last boot: journalctl -u $NAME -b -p emerg..err" >>motd
echo " " >>motd
echo " " >>motd
sudo cp -f motd /etc/motd
rm motd                   # clean up after ourselves
sudo apt remove -y figlet # clean up after ourselves

echo "~~~ installing iterm integration (without utilities) ~~~"
curl -L https://iterm2.com/shell_integration/install_shell_integration.sh| bash

echo "~~~ change directory after connecting ~~~"
echo "cd /opt/$NAME" >> ~/.bash_profile
echo "source .venv/bin/activate" >> ~/.bash_profile

echo "~~~ redirect requests on port 80 to 8080 ~~~~"
sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
echo iptables-persistent iptables-persistent/autosave_v4 boolean true | sudo debconf-set-selections
echo iptables-persistent iptables-persistent/autosave_v6 boolean true | sudo debconf-set-selections
sudo apt install -y iptables-persistent

echo "~~~ avoid writing syslog ~~~"
sudo mkdir /etc/rsyslog.d
echo ":programname, isequal, \"$NAME\" stop" | sudo tee -a /etc/rsyslog.d/filter-$NAME.conf
echo ":programname, isequal, \"$NAME-admin\" stop" | sudo tee -a /etc/rsyslog.d/filter-$NAME-admin.conf

echo "~~~ turn on poe fan only at higher temperatures ~~~"
echo "# PoE Hat Fan Speeds" | sudo tee -a /boot/config.txt
echo "dtparam=poe_fan_temp0=60000" | sudo tee -a /boot/config.txt
echo "dtparam=poe_fan_temp1=70000" | sudo tee -a /boot/config.txt
echo "dtparam=poe_fan_temp2=80000" | sudo tee -a /boot/config.txt
echo "dtparam=poe_fan_temp3=90000" | sudo tee -a /boot/config.txt

echo "~~~ install venv ~~~"
python3 -m venv .venv
source .venv/bin/activate
python3 -m ensurepip

#curl -LsSf https://astral.sh/uv/install.sh | sh
#source $HOME/.cargo/env
#uv venv
#source .venv/bin/activate

echo "~~~ install  ~~~"
setup/install-$NAME.sh
