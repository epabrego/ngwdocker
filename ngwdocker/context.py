import io
import importlib
from pathlib import Path
from shutil import rmtree
from collections import OrderedDict
from copy import deepcopy

import yaml
from loguru import logger

from .package import PackageBase
from .image import Image
from .util import read_envfile, write_envfile, git_checkout


class Context:

    def __init__(self, path, settings):
        self.path = path
        self.settings = settings

        self.mode = settings.get('mode', 'development').lower()
        self.python3 = settings.get('python3', False)

        if 'registry' not in self.settings:
            self.settings['registry'] = dict()

        self.registry_prefix = self.settings['registry'].get('prefix', None)
        self.registry_suffix = self.settings['registry'].get('suffix', None)
        self.registry_version = self.settings['registry'].get('version', None)

        if 'stack' not in self.settings:
            self.settings['stack'] = dict()
        self.stack_enabled = len(self.settings['stack']) > 0
        self.stack_placement = self.settings['stack'].get('placement')

        self.autoload = settings.get('autoload', True)
        if 'package' not in self.settings:
            self.settings['package'] = dict()

        self.package_path = path / 'package'
        self.build_path = path / 'build'

        self.packages = OrderedDict()

        self.images = OrderedDict()
        self.services = OrderedDict()
        self.volumes = OrderedDict()
        
        self.envfile = None
        self.default_instance = True

    @classmethod
    def from_file(cls, filename):
        if filename.exists():
            with io.open(filename, 'r') as fd:
                settings = yaml.safe_load(fd)
        else:
            logger.warning(
                "File '{}' not found! Using default configuration.",
                filename)

            settings = dict(
                mode='development',
                python3=False,
                package=dict()
            )

        return cls(path=filename.parent, settings=settings)

    def load_packages(self):
        if not self.package_path.is_dir():
            logger.info("Creating [package] directory...")
            self.package_path.mkdir()
        
        if not self.build_path.is_dir():
            logger.info("Creating [build] directory...")
            self.build_path.mkdir()

        def load_package(pname, module, cls, path):
            package = cls(pname)
            package.module = module
            package.context = self
            package.path = path

            psettings = self.settings['package'].get(pname, dict())
            if psettings is None:
                psettings = dict()
            package.settings = psettings

            self.packages[pname] = package

        from . import base
        load_package(
            'ngwdocker', base, base.Package,
            Path(__file__).parent / 'base')

        # Package nextgisweb should be loaded first!
        def _skey(pname):
            return (0 if pname == 'nextgisweb' else 1, pname)

        def iter_package():
            if self.autoload:
                for tpth in self.package_path.iterdir():
                    if not tpth.is_dir() or tpth.name.startswith('.'):
                        continue
                    yield tpth.name
            else:
                for k in self.settings['package'].keys():
                    if k == 'ngwdocker':
                        continue
                    tpth = self.package_path / k
                    if not tpth.is_dir():
                        if (
                            self.settings['package'][k] is None or
                            'repository' not in self.settings['package'][k]
                        ):
                            raise RuntimeError(
                                "Package [{}] not found in [{}]!".format(
                                    k, tpth))
                    yield k

        for pname in sorted(iter_package(), key=_skey):
            pth = self.package_path / pname

            pkg_settings = self.settings['package'].get(pname, dict())
            if pkg_settings is None:
                pkg_settings = dict()

            if (
                pkg_settings is False or
                pkg_settings.get('enabled', True) is False
            ):
                continue

            repo_settings = pkg_settings.get('repository')
            if repo_settings is not None:
                logger.debug(
                    'Updating package [{}] from repository [{}]',
                    pname, repo_settings['remote'])
                git_checkout(pth, repo_settings['remote'], repo_settings['revision'])                

            spec = importlib.util.spec_from_file_location(
                "{}.docker".format(pname),
                pth / 'docker.py')
            module = importlib.util.module_from_spec(spec)

            try:
                logger.debug("Loading {}", module)
                spec.loader.exec_module(module)
                pkgcls = module.Package
            except FileNotFoundError:
                logger.warning(
                    "File not found for {}! Using dummy package class.",
                    module)
                pkgcls = PackageBase
                module = None

            load_package(pname, module, pkgcls, pth)

    def initialize(self):
        # Cleanup build directory
        for fp in self.build_path.iterdir():
            if fp.is_file():
                fp.unlink()
            else:
                rmtree(fp)

        self.envfile = read_envfile(self.path / '.env')

        for pname, package in self.packages.items():
            try:
                self._current_package = package
                package.setup()
            finally:
                self._current_package = None

        for pname, package in self.packages.items():
            try:
                self._current_package = package
                package.initialize()
            finally:
                self._current_package = None

        for iname, image in self.images.items():
            image.configure()

        dcompose = OrderedDict()
        dcompose['version'] = '3.7'

        dc_services = dcompose['services'] = OrderedDict()
        stack_warn = False
        for cname, service in self.services.items():
            dc_service = dc_services[cname] = OrderedDict()

            if isinstance(service.image, Image):
                sbuild = dc_service['build'] = OrderedDict()
                sbuild['context'] = str(service.image.path)
                if len(service.image.args) > 0:
                    sbuild['args'] = service.image.args
                if self.registry_prefix is not None:
                    img_name = self.registry_prefix + cname
                    if self.registry_suffix is not None:
                        img_name += self.registry_suffix
                    
                    vflags = list()

                    vflags.append(
                        self.registry_version
                        if self.registry_version
                        else 'latest')
                    
                    if self.is_development():
                        vflags.append('dev')
                    
                    vflags.append('py3' if self.python3 else 'py2')

                    vflags.extend(service.image.flags)
                    
                    dc_service['image'] = img_name + (
                        (":" + '-'.join(vflags))
                        if len(vflags) > 0 else "")
            else:
                dc_service['image'] = service.image

            if service.command is not None:
                dc_service['command'] = service.command
            if len(service.environment) > 0:
                dc_service['environment'] = service.environment
            if len(service.ulimits) > 0:
                dc_service['ulimits'] = service.ulimits
            if len(service.volumes) > 0:
                dc_service['volumes'] = service.volumes
            if len(service.ports) > 0:
                dc_service['ports'] = service.ports
            if len(service.depends_on) > 0:
                dc_service['depends_on'] = [c.name for c in service.depends_on]

            if service.restart and self.is_production():
                dc_service['restart'] = 'unless-stopped'

            if self.stack_enabled and self.is_development():
                if not stack_warn:
                    logger.warning('Stack compatible files available only in production mode!')
                    stack_warn = True
            elif self.stack_enabled:
                dc_service['deploy'] = dc_deploy = OrderedDict()
                dc_deploy['replicas'] = 1
                if self.stack_placement is not None:
                    dc_deploy['placement'] = deepcopy(self.stack_placement)
                if service.restart:
                    dc_deploy['restart_policy'] = OrderedDict(condition='on-failure')
                dc_deploy['endpoint_mode'] = 'dnsrr'

        def _volume_sort_key(item):
            if item[0].startswith('data_'):
                return (10, item[0])
            elif item[0].startswith('config_'):
                return (20, item[0])
            elif item[0].startswith('secret'):
                return (30, item[0])
            else:
                return (50, item[0])

        dcompose['volumes'] = OrderedDict(sorted(
            self.volumes.items(),
            key=_volume_sort_key))

        def dict_representer(dumper, data):
            flow_style = False
            if 'type' in data and 'source' in data and 'target' in data:
                flow_style = True
                
            return dumper.represent_mapping(
                'tag:yaml.org,2002:map', data.items(),
                flow_style=flow_style)

        yaml.add_representer(OrderedDict, dict_representer)

        with io.open('docker-compose.yaml', 'w') as fd:
            yaml.dump(dcompose, fd, default_flow_style=False)

        write_envfile(self.path / '.env', self.envfile)

    def add_image(self, image):
        name = image.name

        image.package = self._current_package
        image.path = path = self.build_path / name
        if not path.exists():
            path.mkdir()

        self.images[name] = image
        return image

    def add_service(self, container):
        container.package = self._current_package
        self.services[container.name] = container

    def is_development(self):
        return self.mode == 'development'

    def is_production(self):
        return self.mode == 'production'
