import io
import tarfile
import configparser
from itertools import chain
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from collections import OrderedDict

from ngwdocker.image import Image, ImageEvent, AptEvent, HomeEvent, VirtualenvEvent
from ngwdocker.util import copyfiles, git_ls_files


class AppImage(Image):
    name = 'app'

    class on_apt(AptEvent):
        pass

    class on_home(HomeEvent):
        pass

    class on_package_files(ImageEvent):
        def __init__(self, image, package):
            super().__init__(image)
            self.package = package
            self.files = list()

        def add(self, *files):
            self.files.extend(files)

    class on_virtualenv(VirtualenvEvent):
        pass

    class on_config(ImageEvent):
        pass

    class on_finish(ImageEvent):
        pass

    def __init__(self):
        super().__init__()
        self.default_config_sections = OrderedDict()

    def configurator(self):
        super().configurator()

        apt = self.on_apt(self)
        apt.add_key('https://nextgis.com/key/68514A1DCF0CF9F7.asc')
        apt.add_repository('ppa:nextgis/ppa')

        apt.package('git', 'mc', 'build-essential', 'libssl-dev')
        apt.package(*(
            ('python3', 'python3-dev', 'python3-venv') if self.context.python3
            else ('python', 'python-dev', 'virtualenv', 'python-virtualenv')))

        apt.package(
            'libgdal-dev',
            'libgeos-dev',
            'gdal-bin',
            'g++',
            'libxml2-dev',
            'libxslt1-dev',
            'zlib1g-dev',
            'libjpeg-turbo8-dev',
            'nodejs',
            'postgresql-client',
            'libmagic-dev')

        apt.notify().render()

        home = self.on_home(self)
        home.directory('bin', 'build', 'package', 'backup')
        home.directory('data', 'data/app')
        home.directory('config', 'config/app')
        home.notify().render()

        python_package = list()

        virtualenv = self.on_virtualenv(self, '$NGWROOT/env').notify()
        virtualenv.requirement('uwsgi')

        pth_package = virtualenv.package_path
        for pname, package in self.package.context.packages.items():
            pth_setup_py = package.path / 'setup.py'
            if not pth_setup_py.exists():
                continue

            python_package.append(pname)

            if self.context.is_development():
                # NOTE: Don't use path.glob() here! Sometimes it
                # converts every file name to lower case!
                pkg_files = []
                for f in package.path.iterdir():
                    if f.is_file() and f.name in (
                        'setup.py',
                        'setup.cfg',
                        'VERSION',
                    ):
                        pkg_files.append(f)

                event = self.on_package_files(self, package).notify()
                pkg_files = chain(pkg_files, event.files)
            else:
                pkg_files = git_ls_files(package.path)

            copyfiles(pkg_files, pth_package / pname, package.path)
            virtualenv.package(package)

            if self.context.is_production():
                virtualenv.after_install(
                    '$NGWROOT/env/bin/nextgisweb-i18n -p {} compile'.format(pname))

        virtualenv.notify().render()

        if self.context.is_development():
            self.config_set('core', 'debug', 'true')

        self.config_set('core', 'sdir', '${NGWROOT}/data/app')

        self.config_set('core', 'database.host', 'postgres')
        self.config_set('core', 'database.name', 'nextgisweb')
        self.config_set('core', 'database.user', 'nextgisweb')
        self.config_set('core', 'database.pwfile', '${NGWROOT}/secret/postgres')

        self.config_set('core', 'backup.path', 'backup')
        self.config_set('core', 'backup.filename', 'nextgisweb-%Y%m%d-%H%M%S.ngwbackup')

        self.config_set('pyramid', 'backup.download', 'true')
        
        event_config = self.on_config(self)
        event_config.notify()

        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Copy bin/ files to image
            bin_path = tmp_path / 'bin'
            bin_src = Path(__file__).parent / 'image' / 'app' / 'bin'
            copyfiles([bin_src, ], bin_path, bin_src)

            # Config directory template
            config_path = tmp_path / 'build' / 'config'
            config_path.mkdir(parents=True)
            with tarfile.open(config_path / 'app.tar.gz', 'w:gz') as config_tar:
                config_src = Path(__file__).parent / 'image' / 'app' / 'config' / 'app'
                config_tar.add(config_src, 'app')

            # Default config
            config_file = tmp_path / 'build' / 'config' / 'app' / 'config.ini'
            config_file.parent.mkdir(parents=True)
            config_obj = configparser.ConfigParser(interpolation=None)
            for k, v in self.default_config_sections.items():
                config_obj[k] = v

            with io.open(config_file, 'w') as fd:
                config_obj.write(fd)

            self.copy(tmp_path, '$NGWROOT', chown='$NGWUSER:$NGWUSER')

        self.environment['NGWDOCKER_PACKAGES'] = ' '.join(python_package)

        if self.context.default_instance:
            self.environment['NGWDOCKER_DEFAULT_INSTANCE'] = 'yes'
            self.environment['NGWDOCKER_WAIT_FOR_SERVICE'] = 'yes'
            self.environment['NGWDOCKER_INITIALIZE_DB'] = 'yes'

        if self.context.is_development():
            self.environment['NGWDOCKER_DEVELOPMENT'] = 'yes'

        self.environment['NEXTGISWEB_CONFIG'] = '$NGWROOT/build/config/app/config.ini:$NGWROOT/config/app/config.ini'
        self.environment['NEXTGISWEB_LOGGING'] = '$NGWROOT/config/app/logging.ini'

        self.expose.append('8080')

        self.volume.extend(('$NGWROOT/data', '$NGWROOT/config', '$NGWROOT/backup'))
        self.entrypoint = ['{}/bin/docker-entrypoint'.format(home.home), ]

        if self.context.is_production():
            self.command = ['uwsgi-production', ]
        elif self.context.is_development():
            self.command = ['pserve-development', ]

        on_finish = self.on_finish(self)
        on_finish.notify()

    def config_set(self, component, option, value=None):
        section = self.default_config_sections.get(component)
        if section is None:
            section = self.default_config_sections[component] = OrderedDict()

        if value is not None:
            section[option] = value
        else:
            del section[option]
