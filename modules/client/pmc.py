from portablemc import cli, Version
import portablemc
import portablemc_forge as pmcf
from os import path
import sys
import threading
from typing import Optional, Tuple

class ForgeVersionInstaller(pmcf.ForgeVersionInstaller):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("Installer Modified")
        self.jvm_exec = "/usr/bin/java"

def new_version(ctx: cli.CliContext, version_id: str) -> Version:
    return version

pmc_http_request = portablemc.http_request

def http_request(url: str, method: str, *,
                 data: Optional[bytes] = None,
                 headers: Optional[dict] = None,
                 timeout: Optional[float] = None,
                 rcv_headers: Optional[dict] = None) -> Tuple[int, bytes]:
    if headers is None:
        headers = {}
    if not "User-Agent" in headers:
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    return pmc_http_request(url, method, data=data, headers=headers, timeout=timeout, rcv_headers=rcv_headers)

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
        pmc.http_request = http_request
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