#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
USERNAME=`whoami`
CURRENT_DIR=`pwd`
PARENT_DIR=`echo $CURRENT_DIR | sed -i "s/\/mcAI//g"`
ID=`printf "%02d" $2`
PID1=`ps -p 1 -o comm=`
if [ "$PID1" = "systemd" ]; then
    echo "Normal Environment, Running Systemd"
else
    echo "Maybe Docker, Chroot or something, Not running Systemd"
fi
set -e

if [ ! -e ~/.xinitrc ]; then
if [ "$PID1" = "systemd" ]; then
bash scripts/change_host.sh client${ID}
bash scripts/change_dns.sh 8.8.8.8
fi
sudo apt update
sudo apt install xserver-xorg xserver-xorg-video-dummy openbox xserver-xorg-xinit -y
sudo tee /usr/share/X11/xorg.conf.d/99-headless.conf << EOF
Section "Monitor"
    Identifier "dummy_monitor"
    DisplaySize 1024 768
EndSection

Section "Device"
    Identifier "dummy_card"
    VideoRam 256000
    Driver "dummy"
EndSection

Section "Screen"
    Identifier "dummy_screen"
    Device "dummy_card"
    Monitor "dummy_monitor"
    SubSection "Display"
    EndSubSection
EndSection
EOF
tee - ~/.xinitrc << EOF
export PATH="~/.local/bin:\$PATH"
bash /home/$USERNAME/startmcai.sh &
exec openbox-session
EOF
fi

sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
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
curl -o ~/.minecraft/mods/OptiFine_1.18.1_HD_U_H4.jar `python scripts/download_optifine.py`
bash modules/client/build_mod.sh
mv ~/*.jar ~/.minecraft/mods
cp modules/client/options.txt ~/.minecraft/
cp -r modules/client/* ~/
cp scripts/chars.json ~/
cp -r mcai/ ~/
rm -rf ~/.config/autostart/setup.desktop

tee ~/startmcai.sh << EOF
cd $CURRENT_DIR/..
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

if [ "$PID1" = "systemd" ]; then
sudo tee /etc/systemd/system/xinitlauncher.service << EOF
[Unit]
Description=xinit launcher
Wants=network-online.target
After=network-online.target

[Service]
ExecStart=/usr/bin/xinit
Restart=always
User=$USERNAME
Type=simple

[Install]
WantedBy=multi-user.target
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
sudo systemctl enable mc_watchdog.timer xinitlauncher.service
sudo reboot
else
sudo tee /init << EOF
#!/bin/bash
cd /home/$USERNAME
sudo -u $USERNAME /usr/bin/xinit
EOF
sudo chmod +x /init
fi