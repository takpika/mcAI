from portablemc import cli, Version
from portablemc_forge import *
from os import path
import sys

class ForgeVersionInstallerMod(ForgeVersionInstaller):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jvm_exec = "/usr/bin/java"

class PortableMinecraft:
    def __init__(self, version, name, resol="256x256", jvm="/usr/bin/java", server="0.0.0.0"):
        self.version = version
        self.name = name
        self.resol = resol
        self.jvm = jvm
        self.server = server
        cli.load_addons()
        self.parser = cli.register_arguments()
        cli.ForgeVersionInstaller = ForgeVersionInstallerMod

    def install(self):
        nsList = ["start", "forge:%s" % self.version, "--dry", "--jvm", self.jvm]
        ns = self.parser.parse_args(nsList)
        cli.cmd_start(ns, cli.new_context(ns))

    def start(self):
        nsList = ["start", "forge:%s" % self.version, "--jvm", self.jvm, "-u", self.name, "--resol", self.resol, "-s", self.server]
        ns = self.parser.parse_args(nsList)
        cli.cmd_start(ns, cli.new_context(ns))

if __name__ == "__main__":
    pmc = PortableMinecraft(sys.argv[1], "setup")
    pmc.install()