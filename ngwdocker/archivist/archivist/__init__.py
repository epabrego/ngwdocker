import sys
import os
import os.path
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from tempfile import mkstemp
from time import sleep, mktime

import click


def backup_options():
    @click.argument('filename', required=False, type=click.Path())
    def wraped(**kwargs):
        return backup(**kwargs)
    return wraped


def backup(filename):
    logger = logging.getLogger('archivist.backup')
    now = datetime.utcnow()

    if filename is None:
        filename = 'backup/archivist-' + now.strftime("%Y%m%d-%H%M%S.tar.zst")

    fpath = Path(filename)
    tmpf = mkstemp(dir=str(fpath.parent), prefix=fpath.name)[1]

    try:
        roots = ['data', 'config', 'secret']
        subprocess.check_call(
            ['tar', '-I', 'zstd', '-cpf', tmpf]
            + roots)
        
        # Wait some time before checking archive
        sleep(1)

        # Check that there is no files with mtime higher
        # than timestamp when backup was started.
        EPOCH = datetime(1970, 1, 1, tzinfo=None)
        tstamp = (now - EPOCH).total_seconds()
        for r in roots:
            check_mtime(Path(r), tstamp)

        # Compare archive contents with current state
        check_tar_compare(tmpf, logger)

        # Rename temporary file to target file name
        # and print its name to stdout.
        os.rename(tmpf, filename)
        print(filename)

    finally:
        if os.path.isfile(tmpf):
            os.unlink(tmpf)


def check_mtime(path, tstamp):
    for f in path.rglob("*"):
        mtime = f.stat().st_mtime
        if mtime > tstamp:
            raise RuntimeError(
                'File %s was changed after backup started (%f > %f)!' % (
                    str(f), mtime, tstamp))


def check_tar_compare(filename, logger):
    subp = subprocess.Popen(
        ['tar', '-I', 'zstd', '--compare', '-f', filename],
        stdout=subprocess.PIPE, universal_newlines=True)
    subp.communicate()
    if subp.returncode != 0:
        fcount = 0
        for line in subp.stdout.split('\n'):
            if line == '':
                continue
            fcount += 1
            logger.error("Comparison failed for %s", line)
        raise RuntimeError("Comparison failed for %d files!" % fcount)


def restore_options():
    @click.argument('filename', type=click.Path())
    def wraped(**kwargs):
        return restore(**kwargs)
    return wraped


def restore(filename):
    lines = subprocess.check_output(
        ['tar', '-I', 'zstd', '-tf', filename],
        universal_newlines=True)

    base = Path('/opt/ngw')
    mpoints = []
    rootdirs = []

    for n in lines.split('\n'):
        if n == '':
            continue
        if n.endswith('/'):
            if n.find('/') == (len(n) - 1):
                rootdirs.append(base / n)
            p = os.path.join(str(base), n)
            if os.path.ismount(p):
                mpoints.append(base / n)

    # Delete everything in directories wich present
    # in archive except mount points.

    def cleanup(path, incl=None):
        clean = True
        for sub in path.iterdir():
            if incl is not None:
                if sub not in incl:
                    continue
            iclean = True
            if sub.is_dir():
                iclean = cleanup(sub)
            if sub not in mpoints:
                if iclean:
                    if sub.is_dir():
                        sub.rmdir()
                    else:
                        sub.unlink()
            else:
                iclean = False
            clean = clean and iclean
        return clean

    cleanup(base, rootdirs)

    subprocess.check_call(['tar', '-I', 'zstd', '-xf', filename])


@click.group()
def main():
    pass


main.command('backup')(backup_options())
main.command('restore')(restore_options())

shortcut_backup = click.command('backup')(backup_options())
shortcut_restore = click.command('restore')(restore_options())
