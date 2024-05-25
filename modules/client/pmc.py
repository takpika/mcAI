import portablemc.cli
import sys
from pathlib import Path
from typing import List, Optional
from subprocess import Popen, PIPE, STDOUT

version = None
mcPID: int | None = None

originalCliRunner = portablemc.cli.CliRunner

class MCCliRunner(originalCliRunner):
    def process_create(self, args: List[str], work_dir: Path) -> Optional[Popen]:
        global mcPID
        process = super().process_create(args, work_dir)
        if process is not None:
            mcPID = process.pid
        return process

class PortableMinecraft:
    def __init__(self, version, name, resol="256x256", jvm="/usr/bin/java", server="0.0.0.0"):
        self.version = version
        self.name = name
        self.resol = resol
        self.jvm = jvm
        self.server = server
        self.running = True
        portablemc.cli.CliRunner = MCCliRunner

    def install(self) -> None:
        global version
        if not self.running: self.running = True
        nsList = ["start", "forge:%s" % self.version, "--dry", "--jvm", self.jvm]
        portablemc.cli.main(nsList)
        self.running = False

    def start(self) -> None:
        global version
        if not self.running: self.running = True
        nsList = ["start", "forge:%s" % self.version, "--jvm", self.jvm, "-u", self.name, "--resol", self.resol, "-s", self.server, "--jvm-args=-Xmx1G"]
        portablemc.cli.main(nsList)
        self.running = False

    def getPID(self) -> int | None:
        return mcPID

if __name__ == "__main__":
    pmc = PortableMinecraft(sys.argv[1], "setup")
    pmc.install()