from portablemc import cli, Version
import portablemc_forge as pmcf
from os import path
import sys
import threading

class ForgeVersionInstaller(pmcf.ForgeVersionInstaller):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("Installer Modified")
        self.jvm_exec = "/usr/bin/java"

def new_version(ctx: cli.CliContext, version_id: str) -> Version:
    return version

version = None

class PortableMinecraft:
    def __init__(self, version, name, resol="256x256", jvm="/usr/bin/java", server="0.0.0.0"):
        self.version = version
        self.name = name
        self.resol = resol
        self.jvm = jvm
        self.server = server
        self.running = True
        cli.load_addons()
        self.parser = cli.register_arguments()
        pmcf.ForgeVersionInstaller = ForgeVersionInstaller

    def install(self):
        global version
        if not self.running: self.running = True
        nsList = ["start", "forge:%s" % self.version, "--dry", "--jvm", self.jvm]
        ns = self.parser.parse_args(nsList)
        self.cmd_watch(ns)
        self.running = False

    def start(self):
        global version
        if not self.running: self.running = True
        nsList = ["start", "forge:%s" % self.version, "--jvm", self.jvm, "-u", self.name, "--resol", self.resol, "-s", self.server, "--jvm-args=-Xmx1G"]
        ns = self.parser.parse_args(nsList)
        self.cmd_watch(ns)
        self.running = False

    def cmd_watch(self, ns):
        t = threading.Thread(target=cli.cmd_start, args=(ns, cli.new_context(ns)))
        t.start()
        t.join()

if __name__ == "__main__":
    pmc = PortableMinecraft(sys.argv[1], "setup")
    pmc.install()