Development and production mode
===============================

**Development mode** (default)
    This mode is for NextGIS Web development. In this mode python package
    sources in ``package/*`` are mounted from docker host with bind. So there is
    no need to rebuild images when changing files. Container processes run under
    same ``uid`` and ``gid`` as local user. So files created inside container
    have same permissions as files created on docker host.

**Production mode**
    Production images can be deployed with ``docker-compose`` (or ``docker
    swarm``). It contains all necessary data and package sources.
