#!/bin/bash
MODULE="client"
USERNAME=`whoami`
MC_VERSION="1.19.4"
set -e
#---Start Script Section---
# $HOME/startmcai.sh
startupScript="
cd $HOME
if [ \"\$FLAVOR\" != \"local\" ]; then
    if [ ! -d mcAI ]; then
        git clone https://github.com/takpika/mcAI.git
    else
        cd mcAI
        git pull
        cd ..
    fi
else
    echo \"[INFO] Local Dev Mode\"
    sleep 3
    sudo pip install debugpy
fi
sudo pip install -r mcAI/modules/$MODULE/requirements.txt
cp -rf mcAI/modules/$MODULE/options.txt $HOME/.minecraft/
cp -rf $HOME/mcAI/modules/$MODULE/* $HOME/
cp -rf $HOME/mcAI/mcai/ $HOME/
cp -rf $HOME/mcAI/scripts/* $HOME/
if [ \"\$FLAVOR\" != \"local\" ]; then
    python $HOME/main.py
else
    python -m debugpy --wait-for-client --listen 0.0.0.0:12888 mcAI/modules/$MODULE/main.py
fi
"

# /etc/systemd/system/xinit.service
xinitService="
[Unit]
Description=X11 session for $USERNAME
After=graphical.target systemd-user-sessions.service network-online.target

[Service]
User=$USERNAME
WorkingDirectory=~
PAMName=login
Environment=XDG_SESSION_TYPE=x11
TTYPath=/dev/tty8
StandardInput=tty
UnsetEnvironment=TERM
UtmpIdentifier=tty8
UtmpMode=user
StandardOutput=journal
ExecStartPre=/usr/bin/chvt 8
ExecStart=/usr/bin/startx -- vt8 -keeptty -verbose 3 -logfile /dev/null
Restart=always

[Install]
WantedBy=graphical.target
"

# /etc/systemd/system/mc_watchdog.service
watchdogService="
[Unit]
Description=Minecraft Watchdog

[Service]
Type=simple
ExecStart=/bin/bash -c \"if (! ps ax | grep main.py | grep -q -v grep); then reboot; fi\"

[Install]
WantedBy=multi-user.target
"

# /etc/systemd/system/mc_watchdog.timer
watchdogTimer="
[Unit]
Description=Minecraft Watchdog Timer

[Timer]
OnBootSec=5min
OnUnitActiveSec=10s
Unit=mc_watchdog.service

[Install]
WantedBy=multi-user.target
"

# /usr/share/X11/xorg.conf.d/99-headless.conf
headlessConf="
Section \"Monitor\"
    Identifier \"dummy_monitor\"
    DisplaySize 1024 768
EndSection

Section \"Device\"
    Identifier \"dummy_card\"
    VideoRam 256000
    Driver \"dummy\"
EndSection

Section \"Screen\"
    Identifier \"dummy_screen\"
    Device \"dummy_card\"
    Monitor \"dummy_monitor\"
    SubSection \"Display\"
    EndSubSection
EndSection

Section \"Extensions\"
    Option \"MIT-SHM\" \"Disable\"
EndSection
"

# $HOME/.xinitrc
xinitrcScript="
export PATH=\"$HOME/.local/bin:\$PATH\"
openbox-session &
bash $HOME/startmcai.sh
"

# /init
initScript="
#!/bin/bash
rm /tmp/.X0-lock
cd $HOME
if [ -n \$CENTRAL_SERVICE_HOST ]; then
echo \$CENTRAL_SERVICE_HOST > $HOME/central_host
fi
sudo -u $USERNAME -E /usr/bin/xinit
"

#---End Script Section---

checkEnv() {
    if [ "$FLAVOR" = "local" ]; then
        echo "[INFO] Running as Local Dev Environment"
        sleep 3
    fi
}

checkPID1() {
    PID1=`ps -p 1 -o comm=`
    if [ "$PID1" = "systemd" ]; then
        echo "[INFO] systemd Environment"
    else
        echo "[INFO] Non-systemd Environment"
    fi

    if [ "$PID1" = "systemd" ]; then
        echo "[INFO] Changing system settings"
        bash scripts/change_host.sh client${ID} > /dev/null
        bash scripts/change_dns.sh 8.8.8.8 > /dev/null
    fi
}

setupGUI() {
    if [ ! -e $HOME/.xinitrc ]; then
        echo "[INFO] Setting up GUI Environment"
        sudo apt update > /dev/null
        echo "[INFO] Installing GUI Environment"
        DEBIAN_FRONTEND=noninteractive sudo apt install xserver-xorg xserver-xorg-video-`if [ "$PID1" = "systemd" ]; then echo "fbdev"; else echo "dummy"; fi` openbox xinit -y > /dev/null
        if [ "$PID1" != "systemd" ]; then
            sudo sed -ie "s/console/anybody/g" /etc/X11/Xwrapper.config  > /dev/null
            echo "$headlessConf" | sudo tee /usr/share/X11/xorg.conf.d/99-headless.conf > /dev/null
            sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target > /dev/null
        fi
        echo "$xinitrcScript" | tee $HOME/.xinitrc > /dev/null
    fi
}

installPackages() {
    echo "[INFO] Fetching package list"
    sudo apt update > /dev/null
    echo "[INFO] Installing apt packages"
    DEBIAN_FRONTEND=noninteractive sudo apt install openjdk-17-jdk python3 python-is-python3 python3-pip python3-tk python3-dev scrot git cifs-utils xinput inetutils-ping psmisc watchdog libgl1-mesa-dev curl libglib2.0-0 -y > /dev/null
    echo "[INFO] Installing Python libraries"
    sudo pip install -r modules/$MODULE/requirements.txt > /dev/null
    if [ "$FLAVOR" = "local" ]; then
        echo "[INFO] Installing Debug Python library"
        sudo pip install debugpy > /dev/null
    fi
}

setupMC() {
    echo "[INFO] Start Install Minecraft"
    echo "export PATH=\"$HOME/.local/bin:\$PATH\"" | tee -a $HOME/.bashrc > /dev/null
    source $HOME/.bashrc
    echo "[INFO] Building Minecraft Mod"
    if [ ! -d $HOME/.minecraft/mods ]; then
        mkdir -p $HOME/.minecraft/mods > /dev/null
    fi
    bash modules/client/build_mod.sh
    mv $HOME/*.jar $HOME/.minecraft/mods
    cp -rf modules/client/options.txt $HOME/.minecraft/
    cp -rf modules/client/* $HOME/
    cp -rf scripts/chars.json $HOME/
    cp -rf mcai/ $HOME/
    echo "[INFO] Installing Minecraft Forge"
    python modules/client/pmc.py $MC_VERSION > /dev/null
}

writeFiles() {
    echo "[INFO] Writing scripts"
    echo "$startupScript" | tee $HOME/startmcai.sh > /dev/null
    if [ "$PID1" = "systemd" ]; then
        echo "$xinitService" | sudo tee /etc/systemd/system/xinit.service > /dev/null
        echo "$watchdogService" | sudo tee /etc/systemd/system/mc_watchdog.service > /dev/null
        echo "$watchdogTimer" | sudo tee /etc/systemd/system/mc_watchdog.timer > /dev/null
        sudo systemctl daemon-reload > /dev/null
        sudo systemctl enable mc_watchdog.timer xinit.service > /dev/null
        echo "Installation complete! This PC will restart in 3 seconds."
        sleep 3
        sudo reboot
    else
        echo "$initScript" | sudo tee /init > /dev/null
        sudo chmod +x /init > /dev/null
    fi
}

main() {
    checkEnv
    checkPID1
    setupGUI
    installPackages
    setupMC
    writeFiles
    echo "[INFO] Installation finished!"
}

main