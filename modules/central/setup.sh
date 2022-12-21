#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
MODULE="central"
USERNAME=`whoami`
CURRENT_DIR=`pwd`
PID1=`ps -p 1 -o comm=`
if [ "$PID1" = "systemd" ]; then
    echo "Normal Environment, Running Systemd"
else
    echo "Maybe Docker, Chroot or something, Not running Systemd"
fi

if [ "$PID1" = "systemd" ]; then
bash scripts/change_host.sh client${ID}
bash scripts/change_dns.sh 8.8.8.8
fi
set -e
sudo apt update
DEBIAN_FRONTEND=noninteractive sudo apt install python3 python3-pip python-is-python3 watchdog -y
sudo pip install -r modules/$MODULE/requirements.txt
tee ~/startmcai.sh << EOF
cd $CURRENT_DIR/..
if [ ! -d mcAI ]; then
    git clone https://github.com/takpika/mcAI.git
else
    cd mcAI
    git pull
    cd ..
fi
sudo pip install -r mcAI/modules/$MODULE/requirements.txt
cp mcAI/modules/$MODULE/* ~/
python ~/main.py ~/configure.json
EOF
if [ "$PID1" = "systemd" ]; then
sudo tee /etc/systemd/system/minecraft.service << EOF
[Unit]
Description=Minecraft AI Central Server
After=network.target network-online.target

[Service]
Type=simple
ExecStart=bash $HOME/startmcai.sh
WorkingDirectory=$HOME
User=$USERNAME
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable --now minecraft
else
sudo tee /init << EOF
#!/bin/bash
cd $HOME
sudo -u $USERNAME bash $HOME/startmcai.sh
EOF
sudo chmod +x /init
fi