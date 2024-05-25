import portablemc.cli
import sys

version = None

class PortableMinecraft:
    def __init__(self, version, name, resol="256x256", jvm="/usr/bin/java", server="0.0.0.0"):
        self.version = version
        self.name = name
        self.resol = resol
        self.jvm = jvm
        self.server = server
        self.running = True

    def install(self):
        global version
        if not self.running: self.running = True
        nsList = ["start", "forge:%s" % self.version, "--dry", "--jvm", self.jvm]
        portablemc.cli.main(nsList)
        self.running = False

    def start(self):
        global version
        if not self.running: self.running = True
        nsList = ["start", "forge:%s" % self.version, "--jvm", self.jvm, "-u", self.name, "--resol", self.resol, "-s", self.server, "--jvm-args=-Xmx1G"]
        portablemc.cli.main(nsList)
        self.running = False

if __name__ == "__main__":
    pmc = PortableMinecraft(sys.argv[1], "setup")
    pmc.install()