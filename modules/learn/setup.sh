#!/bin/bash
USERNAME=`whoami`
bash scripts/change_host.sh learn
bash scripts/change_dns.sh 8.8.8.8
set -e
sudo apt update
sudo apt install python3 python-is-python3 python3-pip python3-dev git cifs-utils inetutils-ping watchdog libgl1-mesa-dev -y
tee -a ~/.bashrc << EOF
export PATH="~/.local/bin:\$PATH"
EOF
source ~/.bashrc
sudo pip install -r modules/learn/requirements.txt
if [ ! -d ~/.minecraft/mods ]; then
mkdir -p ~/.minecraft/mods
fi
cp -r modules/learn/* ~/
cp scripts/chars.json ~/
cp -r mcai/ ~/
tee ~/startmcai.sh << EOF
if [ ! -d mcAI ]; then
    git clone https://github.com/takpika/mcAI.git
else
    cd mcAI
    git pull
    cd ..
fi
cp -r modules/mcAI/learn/* ~/
cp mcAI/scripts/chars.json ~/
cp -r mcAI/mcai/ ~/
python ~/main.py -i $1
EOF
sudo tee /etc/systemd/system/minecraft.service << EOF
[Unit]
Description=Minecraft AI Learning Server
After=network.target network-online.target

[Service]
Type=simple
ExecStart=bash /home/$USERNAME/startmcai.sh
WorkingDirectory=/home/$USERNAME
User=$USERNAME
Restart=Always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable --now minecraft