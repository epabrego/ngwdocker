import io
from packaging.version import Version
from loguru import logger


class PackageBase(object):

    def __init__(self, name):
        self.name = name

    def options(self, func):
        return func

    def debpackages(self):
        return ()

    def envsetup(self):
        pass

    def setup(self):
        pass

    def initialize(self):
        pass

    @property
    def target(self):
        return "$NGWROOT/package/{}".format(self.name)

    @property
    def version(self):
        if hasattr(self, '_version'):
            return self._version

        vfile = self.path / 'VERSION'
        if vfile.is_file():
            with io.open(vfile, 'r') as fd:
                vstr = fd.read().rstrip()
            self._version = Version(vstr)
            logger.debug("Package [{}] version is [{}].", self.name, vstr)
            return self._version

        logger.warning(
            "Version information not available for package [{}]. "
            "File [{}] not found!", self.name, vfile)
        return None
