from portablemc import cli, Version
import portablemc_forge as pmcf
from os import path
import sys

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
        cli.load_addons()
        self.parser = cli.register_arguments()
        pmcf.ForgeVersionInstaller = ForgeVersionInstaller

    def install(self):
        global version
        nsList = ["start", "forge:%s" % self.version, "--dry", "--jvm", self.jvm]
        ns = self.parser.parse_args(nsList)
        cli.cmd_start(ns, cli.new_context(ns))

    def start(self):
        global version
        nsList = ["start", "forge:%s" % self.version, "--jvm", self.jvm, "-u", self.name, "--resol", self.resol, "-s", self.server]
        ns = self.parser.parse_args(nsList)
        cli.cmd_start(ns, cli.new_context(ns))

if __name__ == "__main__":
    pmc = PortableMinecraft(sys.argv[1], "setup")
    pmc.install()