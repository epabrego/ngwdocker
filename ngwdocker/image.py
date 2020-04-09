import os
import platform
import re
import io
import shutil
from collections import OrderedDict
from pathlib import Path
from tempfile import TemporaryDirectory

from zope.event import notify
from zope.event.classhandler import handler

from .util import ndjson, git_commit, git_dirty


class Image:
    name = None

    def __init__(self):
        self.base = 'ubuntu:18.04'
        self.locale = 'C.UTF-8'

        self.dockerfile = list()
        self.copy_idx = 0
        self.volume = list()
        self.expose = list()
        self.entrypoint = None
        self.command = None
        self.environment = OrderedDict()
        self.args = OrderedDict()

        self.flags = list()

    @property
    def context(self):
        return self.package.context

    def configure(self):
        """ Prepeare image dockerfile and auxilary files. """
        self.write('FROM {}'.format(self.base))
        self.write('ENV LC_ALL={}'.format(self.locale))
        self.write('')

        # Add common package to separate layer for caching
        preapt = AptEvent(self)
        preapt.package('curl', 'ca-certificates', 'gnupg', 'software-properties-common')
        preapt.notify().render()

        self.configurator()

        self.close()

    def configurator(self):
        pass

    def close(self):
        if len(self.volume) > 0:
            self.write('VOLUME ' + ndjson(self.volume), '')

        if len(self.expose) > 0:
            self.write('EXPOSE ' + ' '.join(self.expose))

        if self.entrypoint is not None:
            self.write('ENTRYPOINT ' + ndjson(self.entrypoint), '')

        if self.command is not None:
            self.write('CMD ' + ndjson(self.command), '')

        for k, v in self.environment.items():
            self.write('ENV {} {}'.format(k, v))

        with io.open(self.path / 'Dockerfile', 'w') as fd:
            for l in self.dockerfile:
                fd.write(l + '\n')

    def write(self, *lines):
        self.dockerfile.extend(lines)

    def run(self, commands, sep=False):
        self.write('RUN ' + '; \\\n    '.join(
            ['set -ex', ] + [
                cmd.replace('\n', ' \\\n    ')
                for cmd in commands]))
        if sep:
            self.write('')

    def copy(self, source, target, chown=None):
        ctx_name = str(target).lower()
        ctx_name = re.sub(r'[^a-z0-9\-_]', '_', ctx_name, flags=re.I)
        ctx_name = re.sub(r'_{2, }', '_', ctx_name, flags=re.I)
        ctx_name = re.sub(r'(?:^_)|(?:_$)', '', ctx_name, flags=re.I)

        self.copy_idx += 1
        ctx_name = '{:02d}-{}'.format(self.copy_idx, ctx_name)

        if source.is_file():
            shutil.copy2(source, self.path / ctx_name)
        else:
            shutil.copytree(source, self.path / ctx_name, symlinks=True)
        self.write('COPY {} {} {}'.format(
            '' if chown is None else ('--chown=' + chown),
            ctx_name, target))

    def add_flag(self, flag):
        self.flags.append(flag)


class ImageEvent:

    def __init__(self, image):
        self.image = image

    @classmethod
    def handler(cls, function):
        @handler(cls)
        def _handler(event):
            function(event)

    def notify(self):
        notify(self)
        return self


class AptEvent(ImageEvent):

    def __init__(self, image):
        super().__init__(image)
        self.packages = list()
        self.commands = [
            'export DEBIAN_FRONTEND=noninteractive',
            'apt-get update',
        ]
        self.commands_cleanup = [
            'rm -rf /var/lib/apt/lists/*'
        ]

    def add_key(self, url):
        self.commands.append(
            "curl --silent {} | APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=DontWarn "
            "apt-key add - > /dev/null".format(url))

    def add_repository(self, repo):
        self.commands.append('add-apt-repository --yes "{}"'.format(repo))

    def package(self, *packages):
        self.packages.extend(packages)

    def pop(self):
        if len(self.packages) > 0:
            self.commands.extend([
                'apt-get --yes -qq install --no-install-recommends \n    '
                + ' '.join(self.packages)])
            self.packages = list()

    def command(self, *commands):
        self.commands.extend(commands)

    def cleanup(self, *commands):
        self.commands_cleanup.extend(commands)

    def get_commands(self):
        self.pop()
        return self.commands + self.commands_cleanup

    def render(self):
        self.image.run(self.get_commands(), sep=True)


class HomeEvent(ImageEvent):

    def __init__(self, image, user='ngw'):
        super().__init__(image)

        self.user = user
        self.home = '/opt/ngw'

        is_linux = platform.system() == 'Linux'
        is_root = is_linux and os.getuid() == 0

        if image.context.is_development() and is_linux and not is_root:
            self.uid = os.getuid()
            self.gid = os.getgid()
        else:
            self.uid = 1000
            self.gid = 1000

        self.commands = list()
        self.directories = list()

    def command(self, *commands):
        self.commands.extend(commands)

    def directory(self, *directories):
        self.directories.extend(directories)

    def render(self):
        self.image.write(
            'ARG NGWUSER={}'.format(self.user),
            'ARG NGWROOT={}'.format(self.home),
            '')

        self.image.run([
            'groupadd -g {} $NGWUSER'.format(self.gid),
            'useradd --home-dir $NGWROOT -u {} -g $NGWUSER $NGWUSER'.format(self.uid),
            'mkdir -p $NGWROOT ' + ' '.join(['$NGWROOT/' + d for d in self.directories]),
        ] + self.commands + ['chown -R $NGWUSER:$NGWUSER $NGWROOT', ], sep=True)

        self.image.write(
            'WORKDIR $NGWROOT',
            'USER $NGWUSER',
            '')

        self.image.environment['NGWROOT'] = '$NGWROOT'
        self.image.environment['NGWUSER'] = '$NGWUSER'


class VirtualenvEvent(ImageEvent):

    def __init__(self, image, path):
        super().__init__(image)
        self.path = path
        self.requirements = list()
        self.commands_prepare = list()
        self.commands_before_install = list()
        self.commands_after_install = list()

        self.package_tmpdir = TemporaryDirectory()
        self.ngwroot_path = Path(self.package_tmpdir.name)
        self.package_path = self.ngwroot_path / 'package'
        self.package_path.mkdir()

        if not self.image.context.python3:
            self.before_install('export PYTHONWARNINGS=ignore:DEPRECATION::pip._internal.cli.base_command')  # NOQA: E501

        self.before_install(
            (
                'python3 -m venv' if self.image.context.python3
                else '/usr/bin/virtualenv'
            ) + ' ' + self.path,
            "{}/bin/pip install --upgrade pip setuptools".format(self.path)
        )

    def requirement(self, *requirements):
        self.requirements.extend(requirements)

    def package(self, *packages):
        self.requirements.extend(packages)

    def prepare(self, *commands):
        self.commands_prepare.extend(commands)

    def before_install(self, *commands):
        self.commands_before_install.extend(commands)

    def after_install(self, *commands):
        self.commands_after_install.extend(commands)

    def get_commands(self):
        install = []
        cmd_local_version = []

        if len(self.requirements) > 0:
            terms = [
                (('-e ' + r.target) if not isinstance(r, str) else r)
                for r in self.requirements]

            install.append(
                self.path + '/bin/pip install --no-cache-dir \n    '
                + '\n    '.join(terms))

        if len(self.requirements) > 0:
            envar_site = False
            for req in self.requirements:
                if isinstance(req, str):
                    continue

                if not envar_site:
                    sp_py = 'import distutils.sysconfig as sc; print(sc.get_python_lib())'
                    cmd_site = "SITE=$({}/bin/python -c '{}')".format(self.path, sp_py)
                    install.append(cmd_site)
                    if self.image.context.is_development():
                        cmd_local_version.append(cmd_site)
                    envar_site = True

                install.extend((
                    "rm $SITE/{0}.egg-link".format(req.name.replace('_', '-')),
                    "ln -s {0}/{1} $SITE/{1}".format(req.target, req.name),
                    "mv {0}/{1}.egg-info $SITE/".format(req.target, req.name)))

                # Replace local version with commit and dirty state
                commit = git_commit(req.path)
                if commit is not None:
                    dirty = git_dirty(req.path)
                    local = commit + ('.dirty' if dirty else '')
                    cmd_local_version.append(
                        "sed -ri 's/^(Version:[^\\+]+).*/\\1+{1}/gi' "
                        "$SITE/{0}.egg-info/PKG-INFO".format(req.name, local))

        cmd_main = (
            self.commands_prepare +
            self.commands_before_install +
            install +
            self.commands_after_install)

        if self.image.context.is_development():
            # Move local version to separate layer in development mode
            return (cmd_main, cmd_local_version)
        else:
            return (cmd_main + cmd_local_version, )

    def render(self):
        self.image.copy(self.ngwroot_path, '$NGWROOT/', chown='$NGWUSER:$NGWUSER')
        for cmd_set in self.get_commands():
            self.image.run(cmd_set, sep=True)


class Service:

    def __init__(self, name, image):
        self.name = name
        self.image = image
        self.command = None
        self.environment = OrderedDict()
        self.ulimits = OrderedDict()
        self.depends_on = list()
        self.volumes = list()
        self.ports = list()
        self.restart = False

    @property
    def context(self):
        return self.package.context

    def add_volume(self, volume, target):
        self.volumes.append(OrderedDict(
            type='volume', source=volume,
            target=target))

    def add_bind(self, path, target):
        self.volumes.append(OrderedDict(
            type='bind', source=path,
            target=target))
