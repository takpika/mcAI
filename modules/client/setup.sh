#!/bin/bash
USERNAME=`whoami`
CURRENT_DIR=`pwd`
bash scripts/change_host.sh client
bash scripts/change_dns.sh 8.8.8.8
set -e
if [ ! -e ~/.config/autostart/setup.desktop ]; then
sudo apt update
sudo apt install gnome-session gnome-terminal gnome-tweaks -y
if [ ! -d ~/.config/autostart ]; then
mkdir -p ~/.config/autostart
fi
tee ~/.config/autostart/setup.desktop << EOF
[Desktop Entry]
Exec=gnome-terminal -- bash -c "cd $CURRENT_DIR; bash $CURRENT_DIR/modules/client/setup.sh $1;bash"
Type=Application
EOF
if [ -e /etc/gdm3/custom.conf ]; then
sudo sed -i -e "s/\#WaylandEnable/WaylandEnable/g" /etc/gdm3/custom.conf
sudo sed -i -e "s/\#  AutomaticLoginEnable/AutomaticLoginEnable/g" /etc/gdm3/custom.conf
sudo sed -i -e "s/\#  AutomaticLogin = user1/AutomaticLogin = $USERNAME/g" /etc/gdm3/custom.conf
else
if [ ! -d /etc/gdm3 ]; then
sudo mkdir -p /etc/gdm3
fi
sudo tee /etc/gdm3/custom.conf << EOF
[daemon]
WaylandEnable=true
AutomaticLoginEnable=true
AutomaticLogin=$USERNAME
EOF
fi
sudo reboot
fi
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
gsettings set org.gnome.desktop.session idle-delay 0
gsettings set org.gnome.desktop.interface enable-animations false
gsettings set org.gnome.desktop.notifications show-banners false
sudo apt update
sudo apt install openjdk-17-jdk python3 python-is-python3 python3-pip python3-tk python3-dev scrot git cifs-utils xinput inetutils-ping psmisc watchdog libgl1-mesa-dev -y
tee -a ~/.bashrc << EOF
export PATH="~/.local/bin:\$PATH"
EOF
source ~/.bashrc
sudo pip install -r modules/client/requirements.txt
if [ ! -d ~/.minecraft/mods ]; then
mkdir -p ~/.minecraft/mods
fi
curl -o ~/.minecraft/mods/OptiFine_1.18.1_HD_U_H4.jar https://optifine.net/downloadx?f=OptiFine_1.18.1_HD_U_H6.jar&x=f711731a24bd378191826cc4762e313f
bash modules/client/build_mod.sh
mv ~/*.jar ~/.minecraft/mods
cp modules/client/options.txt ~/.minecraft/
cp -r modules/client/* ~/
cp scripts/chars.json ~/
cp -r mcai/ ~/
rm -rf ~/.config/autostart/setup.desktop
tee ~/startmcai.sh << EOF
cd $CURRENT_DIR
if [ ! -d mcAI ]; then
    git clone https://github.com/takpika/mcAI.git
else
    cd mcAI
    git pull
    cd ..
fi
cp mcAI/modules/client/options.txt ~/.minecraft/
cp -r mcAI/modules/client/* ~/
cp mcAI/scripts/chars.json ~/
cp -r mcAI/mcai/ ~/
python ~/main.py -i $1
EOF
tee ~/.config/autostart/minecraft.desktop << EOF
[Desktop Entry]
Exec=gnome-terminal -- bash /home/$USERNAME/startmcai.sh
Type=Application
EOF
sudo tee /etc/systemd/system/mc_watchdog.service << EOF
[Unit]
Description=Minecraft Watchdog

[Service]
Type=simple
ExecStart=/bin/bash -c "if (! ps ax | grep main.py | grep -q -v grep); then reboot; fi"

[Install]
WantedBy=multi-user.target
EOF
sudo tee /etc/systemd/system/mc_watchdog.timer << EOF
[Unit]
Description=Minecraft Watchdog Timer

[Timer]
OnBootSec=5min
OnUnitActiveSec=10s
Unit=mc_watchdog.service

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable mc_watchdog.timer
sudo reboot