#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
USERNAME=`whoami`
CURRENT_DIR=`pwd`
PID1=`ps -p 1 -o comm=`
if [ "$PID1" = "systemd" ]; then
    echo "Normal Environment, Running Systemd"
else
    echo "Maybe Docker, Chroot or something, Not running Systemd"
fi

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
if [ "$PID1" = "systemd" ]; then
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
else
sudo tee /init << EOF
#!/bin/bash
cd /home/$USERNAME
sudo -u $USERNAME bash /home/$USERNAME/startmcai.sh
EOF
sudo chmod +x /init
fi