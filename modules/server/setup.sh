#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
MODULE="server"
USERNAME=`whoami`
CURRENT_DIR=`pwd`
MC_VERSION="1.19.4"
FORGE_VERSION="45.0.57"
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
cp -rf $HOME/mcAI/modules/$MODULE/* $HOME/
cp -rf $HOME/mcAI/mcai/ $HOME/
if [ \"\$FLAVOR\" != \"local\" ]; then
    python $HOME/main.py
else
    python -m debugpy --wait-for-client --listen 0.0.0.0:12888 mcAI/modules/$MODULE/main.py
fi
"

# /etc/systemd/system/minecraft.service
systemdService="
[Unit]
Description=Minecraft Server for AI
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
"

# /init
initFile="
#!/bin/bash
cd $HOME
if [ -n \$CENTRAL_SERVICE_HOST ]; then
    echo \$CENTRAL_SERVICE_HOST > $HOME/central_host
fi
chown -R $USERNAME:$USERNAME $HOME/server
chown -R $USERNAME:$USERNAME $HOME/world
sudo -u $USERNAME -E bash $HOME/startmcai.sh
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

installPackages() {
    echo "[INFO] Fetching package list"
    sudo apt update > /dev/null
    echo "[INFO] Installing apt packages"
    DEBIAN_FRONTEND=noninteractive sudo apt install openjdk-17-jdk python3 python-is-python3 python3-pip cifs-utils screen inetutils-ping watchdog curl -y > /dev/null
    echo "[INFO] Installing Python libraries"
    sudo pip install -r modules/$MODULE/requirements.txt > /dev/null
    if [ "$FLAVOR" = "local" ]; then
        echo "[INFO] Installing Debug Python library"
        sudo pip install debugpy > /dev/null
    fi
}

setupMC() {
    echo "[INFO] Installing Minecraft Server"
    cd $HOME/
    curl -o forge-installer.jar https://maven.minecraftforge.net/net/minecraftforge/forge/${MC_VERSION}-${FORGE_VERSION}/forge-${MC_VERSION}-${FORGE_VERSION}-installer.jar > /dev/null
    java -jar forge-installer.jar --installServer > /dev/null
    echo "eula=true" | tee eula.txt > /dev/null
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
    mkdir -p $HOME/world
    mkdir -p $HOME/server
    mkdir -p $HOME/mods
    for json in {ops,whitelist,usercache,banned-ips,banned-players}.json; do
        if [ -f $HOME/$json ]; then
            rm $HOME/$json
        fi
        touch $HOME/server/$json
        ln -s $HOME/server/$json $HOME/$json
    done
    cd $CURRENT_DIR
    cp -rf modules/server/* $HOME/
    cp -rf mcai/ $HOME/
}

writeFiles() {
    echo "[INFO] Writing scripts"
    echo "$startupScript" | tee $HOME/startmcai.sh > /dev/null
    if [ "$PID1" = "systemd" ]; then
        echo "$systemdService" | sudo tee /etc/systemd/system/minecraft.service > /dev/null
        sudo systemctl enable --now minecraft > /dev/null
    else
        rm -rf $HOME/server
        echo "$initFile" | sudo tee /init > /dev/null
        sudo chmod +x /init
    fi
}

main() {
    checkEnv
    checkPID1
    installPackages
    setupMC
    writeFiles
    echo "[INFO] Installation finished!"
}

main