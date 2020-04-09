import tarfile
from textwrap import dedent
from pathlib import Path
from tempfile import TemporaryDirectory

from ngwdocker.image import Image, ImageEvent, AptEvent, HomeEvent, VirtualenvEvent
from ngwdocker.util import copyfiles


class PostgresImage(Image):
    name = 'postgres'

    class on_apt(AptEvent):
        pass

    class on_home(HomeEvent):
        pass

    class on_virtualenv(VirtualenvEvent):
        pass

    class on_finish(ImageEvent):
        pass

    def __init__(self):
        super().__init__()
        self.postgres_version = "10"
        self.postgis_version = "2.5"

    def configurator(self):
        super().configurator()

        self.write(
            'ENV POSTGRES_MAJOR {}'.format(self.postgres_version),
            'ENV POSTGIS_MAJOR {}'.format(self.postgis_version),
        )

        self.add_flag('postgres' + self.postgres_version.replace('.', ''))
        self.add_flag('postgis' + self.postgis_version.replace('.', ''))

        apt = self.on_apt(self)
        apt.add_key('https://www.postgresql.org/media/keys/ACCC4CF8.asc')
        apt.add_repository('deb http://apt.postgresql.org/pub/repos/apt/ bionic-pgdg main $POSTGRES_MAJOR')

        apt.package('git', 'build-essential', 'libssl-dev')
        apt.package(*(
            ('python3', 'python3-dev', 'python3-venv') if self.context.python3
            else ('python', 'python-dev', 'virtualenv', 'python-virtualenv')))
        apt.package('postgresql-common', 'locales')
        apt.pop()

        apt.command(
            'sed -ri "s/#(create_main_cluster) .*$/\\1 = false/" /etc/postgresql-common/createcluster.conf',
            'localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8')

        apt.package(
            'postgresql-$POSTGRES_MAJOR',
            'postgresql-$POSTGRES_MAJOR-postgis-$POSTGIS_MAJOR',
            'postgresql-$POSTGRES_MAJOR-postgis-$POSTGIS_MAJOR-scripts')

        # Delete default postgres user wich will recreated later
        apt.cleanup('userdel postgres')

        apt.notify().render()

        home = self.on_home(self, user='postgres')
        home.directory('data', 'data/postgres')
        home.directory('config', 'config/postgres')        
        home.directory('secret')
        home.command(
            'chown -R $NGWUSER:$NGWUSER /var/run/postgresql /var/lib/postgresql',
            'ln -s $NGWROOT/data/postgres /var/lib/postgresql/data')
        
        home.notify().render()

        virtualenv = self.on_virtualenv(self, "$NGWROOT/env")
        virtualenv.notify().render()

        self.write("", "ENV POSTGRES_USER nextgisweb")

        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Copy bin/ files to image
            bin_path = tmp_path / 'bin'
            bin_src = Path(__file__).parent / 'image' / 'postgres' / 'bin'
            copyfiles([bin_src, ], bin_path, bin_src)

            # Config directory template
            config_path = tmp_path / 'build' / 'config'
            config_path.mkdir(parents=True)
            with tarfile.open(config_path / 'postgres.tar.gz', 'w:gz') as config_tar:
                config_src = Path(__file__).parent / 'image' / 'postgres' / 'config' / 'postgres'
                config_tar.add(config_src, 'postgres')

            self.copy(tmp_path, '$NGWROOT', chown='$NGWUSER:$NGWUSER')

        self.environment['NGWDOCKER_POSTGRES_INITDB'] = 'yes'
        if self.context.default_instance:
            self.environment['NGWDOCKER_DEFAULT_INSTANCE'] = 'yes'

        self.expose.append('5432')

        self.entrypoint = ['{}/bin/docker-entrypoint'.format(home.home), ]
        self.command = ['postgres', ]

        finish = self.on_finish(self)
        finish.notify()
