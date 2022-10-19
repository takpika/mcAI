#!/bin/bash
CURRENT_DIR=`pwd`
bash scripts/change_host.sh server
bash scripts/change_dns.sh 8.8.8.8
set -e
sudo apt update
sudo apt install openjdk-17-jdk python3 python-is-python3 python3-pip cifs-utils screen inetutils-ping watchdog -y
pip install psutil
wget https://maven.minecraftforge.net/net/minecraftforge/forge/1.18.1-39.0.79/forge-1.18.1-39.0.79-installer.jar
java -jar forge-1.18.1-39.0.79-installer.jar --installServer
tee eula.txt << EOF
eula=true
EOF
if grep -q Xmx1G user_jvm_args.txt ; then
echo Skip user_jvm_args.txt...
else
echo "-Xmx1G -Xms1G" >> user_jvm_args.txt
fi
if grep -q "txt nogui" run.sh ; then
echo Skip run.sh...
else
sed -i -e "s/unix_args.txt/unix_args.txt nogui/g" run.sh
fi
cp modules/server/* ~/
cp -r mcai/ ~/
tee ~/startmcai.sh << EOF
cd $CURRENT_DIR
if [ ! -d mcAI ]; then
    git clone https://github.com/takpika/mcAI.git
else
    cd mcAI
    git pull
    cd ..
fi
cp mcAI/modules/server/* ~/
cp -r mcAI/mcai/ ~/
python ~/main.py -i $1
EOF
sudo tee /etc/systemd/system/minecraft.service << EOF
[Unit]
Description=Minecraft Server for AI
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