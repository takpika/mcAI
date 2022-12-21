#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
MODULE="server"
USERNAME=`whoami`
CURRENT_DIR=`pwd`
MC_VERSION="1.19.2"
FORGE_VERSION="43.2.1"
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
DEBIAN_FRONTEND=noninteractive sudo apt install openjdk-17-jdk python3 python-is-python3 python3-pip cifs-utils screen inetutils-ping watchdog curl -y
sudo pip install -r modules/$MODULE/requirements.txt
cd ~/
curl -o forge-installer.jar https://maven.minecraftforge.net/net/minecraftforge/forge/${MC_VERSION}-${FORGE_VERSION}/forge-${MC_VERSION}-${FORGE_VERSION}-installer.jar
java -jar forge-installer.jar --installServer
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
mkdir -p ~/world
mkdir -p ~/server
mkdir -p ~/mods
curl -o ~/mods/ToughAsNails-${MC_VERSION}.jar https://mediafilez.forgecdn.net/files/3871/450/ToughAsNails-1.19-8.0.0.78.jar
for json in {ops,whitelist,usercache,banned-ips,banned-players}.json; do
    if [ -f ~/$json ]; then
        rm ~/$json
    fi
    touch ~/server/$json
    ln -s ~/server/$json ~/$json
done
cd $CURRENT_DIR
cp modules/server/* ~/
cp -r mcai/ ~/
tee ~/startmcai.sh << EOF
cd $CURRENT_DIR/..
for folder in {world, server}; do
    if [ -d $folder ]; then
        sudo chown -R $USERNAME:$USERNAME \$folder
    else
        mkdir -p \$folder
    fi
done
if [ ! -d mcAI ]; then
    git clone https://github.com/takpika/mcAI.git
else
    cd mcAI
    git pull
    cd ..
fi
sudo pip install -r mcAI/modules/$MODULE/requirements.txt
cp mcAI/modules/$MODULE/* ~/
cp -r mcAI/mcai/ ~/
python ~/main.py
EOF
if [ "$PID1" = "systemd" ]; then
sudo tee /etc/systemd/system/minecraft.service << EOF
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
EOF
sudo systemctl enable --now minecraft
else
rm -rf ~/server
sudo tee /init << EOF
#!/bin/bash
cd $HOME
sudo -u $USERNAME bash $HOME/startmcai.sh
EOF
sudo chmod +x /init
fi