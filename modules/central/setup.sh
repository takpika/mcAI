#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
USERNAME=`whoami`
CURRENT_DIR=`pwd`
bash scripts/change_host.sh central
bash scripts/change_dns.sh 8.8.8.8
set -e
sudo apt update
sudo apt install python3 python3-pip python-is-python3 watchdog -y
tee ~/startmcai.sh << EOF
cd $CURRENT_DIR/..
if [ ! -d mcAI ]; then
    git clone https://github.com/takpika/mcAI.git
else
    cd mcAI
    git pull
    cd ..
fi
cp mcAI/modules/central/* ~/
python ~/main.py ~/configure.json
EOF
sudo tee /etc/systemd/system/minecraft.service << EOF
[Unit]
Description=Minecraft AI Central Server
After=network.target network-online.target

[Service]
Type=simple
ExecStart=bash /home/$USERNAME/startmcai.sh
WorkingDirectory=/home/$USERNAME
User=$USERNAME
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable --now minecraft