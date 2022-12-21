import argparse
import subprocess, os
import random

def main():
    parser = argparse.ArgumentParser(
        prog="install.py",
        description="mcAI Installer",
        add_help = True
    )
    parser.add_argument('-t', '--type',
        help='Server Type',
        type=str,
        choices=['central', 'client', 'learn', 'server'],
        required=True
    )
    parser.add_argument('-i', '--interface',
        help='Network Interface',
        type=str,
        default='eth0',
        required=True
    )
    parser.add_argument('-p', '--ip',
        help='IP Address/Mask',
        type=str,
        required=True
    )
    parser.add_argument('-n', '--number',
        help='Server Number (Client Only)',
        type=int,
        default=0
    )
    args = parser.parse_args()
    devnull = open("/dev/null", "wb")
    process = subprocess.check_output("ps -p 1 -o comm=".split()).decode().replace("\n","")
    if process == "systemd":
        netplanText = """
        network:
            version: 2
            ethernets:
                %s:
                    addresses: [\\\"%s\\\"]
        """ % (args.interface, args.ip)
        netplanFileName = "99-mcAI.yaml"
        if os.path.exists(os.path.join("/etc/netplan", netplanFileName)):
            subprocess.run("sudo rm \"%s\"" % (os.path.join("/etc/netplan", netplanFileName)), shell=True)
        subprocess.run('echo "%s" | sudo tee /etc/netplan/%s' % (netplanText, netplanFileName), shell=True, stdout=devnull)
        subprocess.run('sudo netplan apply', shell=True)
    subprocess.run("bash modules/%s/setup.sh %d" % (args.type, args.number), shell=True)

if __name__ == "__main__":
    main()