#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
MODULE="learn"
USERNAME=`whoami`
set -e

# ---Start Script Section---
# $HOME/startmcai.sh
startupScript="
cd $HOME
if [ -d models ]; then
    sudo chown -R $USERNAME:$USERNAME models
else
    mkdir -p models
fi
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
cp -rf $HOME/mcAI/modules/$MODULE/* $HOME/
cp -rf $HOME/mcAI/mcai/ $HOME/
cp -rf $HOME/mcAI/scripts/* $HOME/
if [ \"\$FLAVOR\" != \"local\" ]; then
    python $HOME/main.py
else
    python -m debugpy --wait-for-client --listen 0.0.0.0:12888 mcAI/modules/$MODULE/main.py
fi
"

# /etc/systemd/system/minecraft.service
systemdService="
[Unit]
Description=Minecraft AI Learning Server
After=network.target network-online.target

[Service]
Type=simple
ExecStart=bash $HOME/startmcai.sh
WorkingDirectory=$HOME
User=$USERNAME
Restart=Always
RestartSec=5

[Install]
WantedBy=multi-user.target
"

# /init
initFile="
#!/bin/bash
cd $HOME
if [ -n \$CENTRAL_SERVICE_HOST ]; then
    echo \$CENTRAL_SERVICE_HOST > $HOME/central_host
fi
chown -R $USERNAME:$USERNAME $HOME/models
sudo -u $USERNAME -E bash $HOME/startmcai.sh
"

# ---End Script Section---

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

installPackages() {
    echo "[INFO] Fetching package list"
    sudo apt update > /dev/null
    echo "[INFO] Installing apt packages"
    DEBIAN_FRONTEND=noninteractive sudo apt install python3 python-is-python3 python3-pip python3-dev git cifs-utils inetutils-ping watchdog libgl1-mesa-dev libglib2.0-0 -y > /dev/null
    echo "[INFO] Installing Python libraries"
    sudo pip install -r modules/$MODULE/requirements.txt > /dev/null
    if [ "$FLAVOR" = "local" ]; then
        echo "[INFO] Installing Debug Python library"
        sudo pip install debugpy > /dev/null
    fi
}

writeFiles() {
    echo "[INFO] Writing scripts"
    echo "export PATH=\"~/.local/bin:\$PATH\"" | tee -a $HOME/.bashrc > /dev/null
    echo "$startupScript" | tee $HOME/startmcai.sh > /dev/null
    if [ "$PID1" = "systemd" ]; then
        echo "$systemdService" | sudo tee /etc/systemd/system/minecraft.service > /dev/null
        sudo systemctl enable --now minecraft > /dev/null
    else
        echo "$initFile" | sudo tee /init > /dev/null
        sudo chmod +x /init
    fi
}

main() {
    checkEnv
    checkPID1
    installPackages
    writeFiles
    mkdir -p $HOME/models
    echo "[INFO] Installation finished!"
}

main