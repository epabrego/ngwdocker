Development mode
================

When to rebuild images
----------------------

Although in development mode package sources are mapped from docker host some
changes requires to rebuild docker images:

* Upgrading ``ngwdocker``
* Changes in ``ngwdocker.yaml``
* Changes in ``setup.py``

Images built with ngwdocker actively use Dockerfile caching so minor changes are
built quickly. So starting an extra build should not be a problem even if
nothing has changed.

.. code-block:: bash

    $ ngwdocker && docker-compose build


Multiple environments on same host
----------------------------------

You can use multiple environments on same host. Just clone this repository into
different directories.

.. code-block:: shell

    $ git clone git@github.com:nextgis/ngwdocker.git ngwdocker_py2
    $ git clone git@github.com:nextgis/ngwdocker.git ngwdocker_py3

You can share ``package`` directory between environments with bind mount (
which requires root access):

.. code-block:: shell

    $ cd ngwdocker_py3
    $ sudo mount --bind ../ngwdocker_py2/package package

Usefull commands during development
-----------------------------------

Run arbitrary ``nextgisweb`` command, ``initialize_db`` for example:

.. code-block:: shell

    $ docker-compose run --rm app nextgisweb initialize_db

or for translating:

.. code-block:: shell

    $ docker-compose run --rm app nextgisweb-i18n --package nextgisweb extract webmap
    $ docker-compose run --rm app nextgisweb-i18n --package nextgisweb update webmap
    $ docker-compose run --rm app nextgisweb-i18n --package nextgisweb compile webmap

Run pytest tests:

.. code-block:: shell

    $ docker-compose run --rm app python -m pytest package/

Start from scratch. so command will **DESTROY** all data, including
database and data files:

.. code-block:: shell

    $ docker-compose down --remove-orphans --volumes