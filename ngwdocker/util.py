import io
import os
import string
import secrets
import json
from datetime import datetime
from shutil import copytree, copy2 as copyfile
from subprocess import check_output, check_call, call, CalledProcessError, DEVNULL


def copyfiles(sources, dst, relative=None):
    for sf in sources:
        subp = sf.relative_to(relative)
        sd = dst.joinpath(subp)
        sd.parent.mkdir(exist_ok=True, parents=True)
        if sf.is_file():
            copyfile(sf, sd, follow_symlinks=False)
        else:
            copytree(sf, sd, symlinks=True)


def ndjson(data):
    """ Dump data as one line json. """
    return json.dumps(data, indent=None)


def read_envfile(path):
    result = dict()
    if path.exists():
        with io.open(path, 'r') as fp:
            for l in fp:
                var, val = l.rstrip('\n').split('=', 1)
                result[var] = val
    return result


def write_envfile(path, values):
    # Keep original file backup on content changes
    original = read_envfile(path)
    if original != values and original != dict():
        suffix = datetime.now().replace(microsecond=0).isoformat() \
            .replace(':', '').replace('-', '').replace('T', '-')
        os.rename(path, path.with_name(path.name + '-' + suffix))

    # Write new file contents
    with io.open(path, 'w') as fd:
        for k, v in values.items():
            fd.write('{}={}\n'.format(k, v))


def pwgen(length=16):
    alphabet = string.ascii_letters + string.digits
    while True:
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and sum(c.isdigit() for c in password) >= 3):
            break
    return password


def git_ls_files(path):
    listing = check_output(
        ['git', 'ls-files', '--exclude-standard'],
        cwd=path, universal_newlines=True)

    for line in listing.split('\n'):
        if line == '':
            continue
        yield path.joinpath(line)


def git_commit(path):
    try:
        commit = check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=path, universal_newlines=True)
    except CalledProcessError as exc:
        if exc.returncode == 128:
            # Not a git repository
            return None
        else:
            raise
    return commit.rstrip()


def git_dirty(path):
    try:
        return call(
            ['git', 'diff', '--no-ext-diff', '--quiet'],
            cwd=path, universal_newlines=True
        ) != 0
    except CalledProcessError as exc:
        if exc.returncode == 128:
            # Not a git repository
            return None
        else:
            raise


def git_checkout(path, remote, revision):
    if not path.exists():
        check_call(
            ['git', 'clone', remote, str(path)],
            stdout=DEVNULL, stderr=DEVNULL)

    check_call(
        ['git', 'fetch', '--all'], cwd=path,
        stdout=DEVNULL, stderr=DEVNULL)

    check_call(
        ['git', 'checkout', revision], cwd=path,
        stdout=DEVNULL, stderr=DEVNULL)
