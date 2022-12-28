from portablemc import cli, Version
from portablemc_forge import *
from os import path
import sys

class PortableMinecraft:
    def __init__(self, version, name, resol="256x256", jvm="/usr/bin/java", server="0.0.0.0"):
        self.version = version
        self.name = name
        self.resol = resol
        self.jvm = jvm
        self.server = server
        self.parser = cli.register_arguments()

    def install(self):
        nsList = ["start", "forge:%s" % self.version, "--dry", "--jvm", self.jvm]
        ns = self.parser.parse_args(nsList)
        self.new_version(cli.new_version, cli.new_context(ns), ns.version)
        cli.cmd_start(ns, cli.new_context(ns))

    def start(self):
        nsList = ["start", "forge:%s" % self.version, "--jvm", self.jvm, "-u", self.name, "--resol", self.resol, "-s", self.server]
        ns = self.parser.parse_args(nsList)
        self.new_version(cli.new_version, cli.new_context(ns), ns.version)
        cli.cmd_start(ns, cli.new_context(ns))

    def new_version(self, old, ctx: cli.CliContext, version_id: str) -> Version:
        print("Installing %s" % version_id)
        if version_id.startswith("forge:"):

            main_dir = path.dirname(ctx.versions_dir)
            if main_dir != path.dirname(ctx.libraries_dir):
                raise ForgeInvalidMainDirectory()

            game_version = version_id[6:]
            if not len(game_version):
                game_version = "release"

            manifest = cli.new_version_manifest(ctx)
            game_version, game_version_alias = manifest.filter_latest(game_version)

            forge_version = None

            # If the version is an alias, we know that the version needs to be resolved from the forge
            # promotion metadata. It's also the case if the version ends with '-recommended' or '-latest',
            # or if the version doesn't contains a "-".
            if game_version_alias or game_version.endswith(("-recommended", "-latest")) or "-" not in game_version:
                promo_versions = request_promo_versions()
                for suffix in ("", "-recommended", "-latest"):
                    tmp_forge_version = promo_versions.get(f"{game_version}{suffix}")
                    if tmp_forge_version is not None:
                        if game_version.endswith("-recommended"):
                            game_version = game_version[:-12]
                        elif game_version.endswith("-latest"):
                            game_version = game_version[:-7]
                        forge_version = f"{game_version}-{tmp_forge_version}"
                        break

            if forge_version is None:
                # If the game version came from an alias, we know for sure that no forge
                # version is currently supporting the latest release/snapshot.
                if game_version_alias:
                    raise ForgeVersionNotFound(ForgeVersionNotFound.MINECRAFT_VERSION_NOT_SUPPORTED, game_version)
                # Test if the user has given the full forge version
                forge_version = game_version

            installer = ForgeVersionInstaller(ctx, forge_version, prefix="forge")
            installer.jvm_exec = self.jvm

            if installer.needed():

                cli.print_task("", "start.forge.resolving", {"version": forge_version})
                installer.prepare()
                cli.print_task("OK", "start.forge.resolved", {"version": forge_version}, done=True)

                installer.check_download(cli.pretty_download(installer.dl))

                cli.print_task("", "start.forge.wrapper.running")
                installer.install()
                cli.print_task("OK", "start.forge.wrapper.done", done=True)

            cli.print_task("INFO", "start.forge.consider_support", done=True)
            return installer.version

        return old(ctx, version_id)

if __name__ == "__main__":
    pmc = PortableMinecraft(sys.argv[1], "setup")
    pmc.install()