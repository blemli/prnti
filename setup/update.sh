set -e
name=$(basename $(git rev-parse --show-toplevel))
cd /opt/$name
git restore setup/*
git stash
git config --global pull.rebase true # todo: bad?
git pull
sudo chmod +x setup/*.sh
. setup/install-$name.sh
sudo service avahi-daemon restart