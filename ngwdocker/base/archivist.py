from pathlib import Path
from itertools import chain

from ..image import Image, AptEvent, HomeEvent, VirtualenvEvent
from ..util import copyfiles, git_ls_files


class ArchivistImage(Image):
    name = "archivist"

    class on_apt(AptEvent):
        pass

    class on_home(HomeEvent):
        pass

    class on_virtualenv(VirtualenvEvent):
        pass

    def configurator(self):
        super().configurator()

        apt = self.on_apt(self)
        apt.package(*(
            ('python3', 'python3-dev', 'python3-venv') if self.context.python3
            else ('python', 'python-dev', 'virtualenv', 'python-virtualenv')))
        apt.package('zstd')
        apt.notify().render()

        home = self.on_home(self)
        home.directory('bin', 'backup')
        home.directory('data', 'data/app', 'data/postgres')
        home.directory('config', 'config/app', 'config/postgres')
        home.directory('secret')
        home.notify().render()

        venv = self.on_virtualenv(self, "$NGWROOT/env")

        # Fake package object wich can be installed
        class Package():
            name = "archivist"
            path = Path(__file__).parent.parent / 'archivist'
            target = "$NGWROOT/archivist"

        apkg = Package()

        if self.context.is_development():
            pkg_files = chain(
                apkg.path.glob('setup.py'),
                apkg.path.glob('setup.cfg'),
                apkg.path.glob('VERSION'))
        else:
            pkg_files = git_ls_files(apkg.path)

        copyfiles(pkg_files, venv.ngwroot_path / apkg.name, apkg.path)

        venv.package(apkg)
        venv.notify().render()

        self.copy(
            Path(__file__).parent / 'image' / 'archivist', '$NGWROOT',
            chown="$NGWUSER:$NGWUSER")

        self.entrypoint = ['{}/bin/docker-entrypoint'.format(home.home), ]
        self.command = ['/bin/bash', ]
