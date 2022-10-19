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
    args = parser.parse_args()
    while True:
        netplanFileName = "99-mcAI.yaml"
        if not os.path.exists(os.path.join("/etc/netplan", netplanFileName)):
            break
        netplanId = random.randint(0, 99)
        netplanFileName = str(netplanId).zfill(2)
    devnull = open("/dev/null", "wb")
    netplanText = """
    network:
        version: 2
        ethernets:
            %s:
                addresses: [\\\"%s\\\"]
    """ % (args.interface, args.ip)
    subprocess.run('echo "%s" | sudo tee /etc/netplan/%s' % (netplanText, netplanFileName), shell=True, stdout=devnull)
    subprocess.run("bash modules/%s/setup.sh %s" % (args.type, args.interface), shell=True)

if __name__ == "__main__":
    main()