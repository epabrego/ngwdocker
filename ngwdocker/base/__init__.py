from collections import OrderedDict
from shutil import copytree
from pathlib import Path

from packaging.version import Version
from loguru import logger

from ngwdocker.package import PackageBase
from ngwdocker.image import Service
from ngwdocker.util import pwgen

from .app import AppImage
from .postgres import PostgresImage
from .archivist import ArchivistImage


class Package(PackageBase):

    def initialize(self):
        pkg_nextgisweb = self.context.packages['nextgisweb']
        cap_secret = pkg_nextgisweb.version is not None and not (
            pkg_nextgisweb.version < Version('3.2.0.dev0'))

        def add_data(svc, svc_name=None):
            if svc_name is None:
                svc_name = svc.name
            vol_name = 'data_{}'.format(svc_name)
            svc.add_volume(vol_name, '/opt/ngw/data/{}'.format(svc_name))
            if vol_name not in self.context.volumes:
                self.context.volumes[vol_name] = OrderedDict()
        
        def add_config(svc, svc_name=None):
            if svc_name is None:
                svc_name = svc.name
            mpoint = '/opt/ngw/config/{}'.format(svc_name)
            
            if self.context.is_development():
                bind_pth = self.context.path / 'config' / svc_name
                bind_pth.mkdir(parents=True, exist_ok=True)
                svc.add_bind('./' + str(bind_pth), mpoint)
            else:
                vol_name = 'config_{}'.format(svc_name)
                svc.add_volume(vol_name, mpoint)
                if vol_name not in self.context.volumes:
                    self.context.volumes[vol_name] = OrderedDict()

        def add_secret(svc):
            if self.context.is_development():
                secret_pth = self.context.path / 'secret'
                secret_pth.mkdir(exist_ok=True)
                svc.add_bind('./' + str(secret_pth), '/opt/ngw/secret')
            else:
                svc.add_volume('secret', '/opt/ngw/secret')
                if 'secret' not in self.context.volumes:
                    self.context.volumes['secret'] = OrderedDict()

        def add_backup(svc):
            if self.context.is_development():
                pth_backup = self.context.path / 'backup'
                if not pth_backup.exists():
                    pth_backup.mkdir()
                svc.add_bind('./' + str(pth_backup), '/opt/ngw/backup')
            else:
                if 'backup' not in self.context.volumes:
                    self.context.volumes['backup'] = OrderedDict()
                svc.add_volume('backup', '/opt/ngw/backup')

        if self.context.default_instance:
            if not cap_secret:
                if 'DATABASE_PASSWORD' not in self.context.envfile:
                    self.context.envfile['DATABASE_PASSWORD'] = pwgen()
                if 'PYRAMID_SECRET' not in self.context.envfile:
                    self.context.envfile['PYRAMID_SECRET'] = pwgen()
            else:
                for envk in ('DATABASE_PASSWORD', 'PYRAMID_SECRET'):
                    if envk in self.context.envfile:
                        logger.warning(
                            "[{}] is present in env file but secret "
                            "volume available.", envk)

        app_img = AppImage()
        self.context.add_image(app_img)

        app_svc = Service('app', app_img)
        app_svc.restart = True
        add_data(app_svc)
        add_config(app_svc)
        add_secret(app_svc)

        if self.context.default_instance:
            if "DATABASE_PASSWORD" in self.context.envfile:
                app_svc.environment['NEXTGISWEB_CORE__DATABASE__PASSWORD'] = '${DATABASE_PASSWORD}'

            if "PYRAMID_SECRET" in self.context.envfile:
                app_svc.environment['NEXTGISWEB_PYRAMID__SECRET'] = '${PYRAMID_SECRET}'

        if self.context.is_development():
            pth_work = self.context.path / 'work'
            if not pth_work.exists():
                pth_work.mkdir()

            app_svc.add_bind('./' + str(pth_work), '/opt/ngw/work')

        add_backup(app_svc)

        if self.context.is_development():
            app_svc.add_bind('./package', '/opt/ngw/package')

        if self.context.default_instance:
            app_svc.ports.append('8080:8080')

        self.context.add_service(app_svc)

        postgres_img = PostgresImage()
        self.context.add_image(postgres_img)

        postgres_svc = Service('postgres', postgres_img)
        postgres_svc.restart = True
        add_data(postgres_svc)
        add_config(postgres_svc)
        add_secret(postgres_svc)

        self.context.add_service(postgres_svc)
        app_svc.depends_on.append(postgres_svc)

        if self.context.default_instance and "DATABASE_PASSWORD" in self.context.envfile:
            postgres_svc.environment['POSTGRES_PASSWORD'] = '${DATABASE_PASSWORD}'

        archivist_img = ArchivistImage()
        self.context.add_image(archivist_img)

        archivist_svc = Service('archivist', archivist_img)
        archivist_svc.restart = True
        self.context.add_service(archivist_svc)

        add_data(archivist_svc, 'app')
        add_data(archivist_svc, 'postgres')
        add_config(archivist_svc, 'app')
        add_config(archivist_svc, 'postgres')
        add_secret(archivist_svc)

        add_backup(archivist_svc)

        if self.context.is_development():
            apath = (Path(__file__).parent.parent / 'archivist').resolve()
            try:
                apath = './' + str(apath.relative_to(Path('.').resolve()))
            except ValueError:
                pass

            archivist_svc.add_bind(str(apath), '/opt/ngw/archivist')

        pgadmin_st = self.settings.get('pgadmin', dict())
        if pgadmin_st.get('enabled', False) is True:
            pgadmin_svc = Service('pgadmin', 'dpage/pgadmin4')
            self.context.add_service(pgadmin_svc)

            pgadmin_svc.environment['PGADMIN_DEFAULT_EMAIL'] = 'ngwdocker@localhost'
            pgadmin_svc.environment['PGADMIN_DEFAULT_PASSWORD'] = 'ngwdocker'

            pgadmin_svc.depends_on.append(postgres_svc)
            pgadmin_svc.ports.append('8432:80')

        elasticsearch_st = self.settings.get('elasticsearch', dict())
        if elasticsearch_st.get('enabled', False) is True:
            elasticsearch_image = 'docker.elastic.co/elasticsearch/elasticsearch:7.5.1'
            elasticsearch_svc = Service('elasticsearch', elasticsearch_image)
            elasticsearch_svc.restart = True

            self.context.add_service(elasticsearch_svc)
            app_svc.depends_on.append(elasticsearch_svc)

            elasticsearch_svc.environment['cluster.name'] = 'ngwdocker'
            elasticsearch_svc.environment['discovery.type'] = 'single-node'

            elasticsearch_svc.ulimits['memlock'] = OrderedDict(soft=-1, hard=-1)

            self.context.volumes['elasticsearch'] = {}
            elasticsearch_svc.add_volume('elasticsearch', '/usr/share/elasticsearch/data')

            elasticsearch_svc.ports.append('8920:9200')

        kibana_st = self.settings.get('kibana', dict())
        if kibana_st.get('enabled', False) is True:
            kibana_img = 'docker.elastic.co/kibana/kibana:7.5.1'
            kibana_svc = Service('kibana', kibana_img)
            kibana_svc.restart = True

            self.context.add_service(kibana_svc)
            kibana_svc.depends_on.append(elasticsearch_svc)

            kibana_svc.environment['SERVER_NAME'] = 'ngwdocker'
            kibana_svc.environment['ELASTICSEARCH_HOSTS'] = 'http://elasticsearch:9200'

            kibana_svc.ports.append('8561:5601')
