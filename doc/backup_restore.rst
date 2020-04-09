Backup and restore
==================

Default backup destination
--------------------------

NextGIS Web Docker configuration provides default destination for created
backup files. By default it is located in ``/opt/ngw/backup`` directory
and mounted as docker volume. So if the file name for the backup is not 
specified, it is automatically created in this directory. Since directory
``/opt/ngw`` is used by default, the archive path will look like
``backup/some-filename-with-extension``.

Offline backups with archivist
------------------------------

NextGIS Web Docker stores all data inside docker volumes. For convenient
data backup, the package provides ``archivist`` tool that copies all from
volumes the data to a file.

Since files can be modified during copying, this tool only works in *offline
mode*. All services modifying files must be stopped before copying.

Technically an archive created using ``archivist`` is a *GNU Tar* archive
compressed using the *zstandard library* with default extension ``.tar.zst``.
The archive contains data from all components and services, including
PostgreSQL data and NextGIS Web file storage.


.. warning::

    Remember to stop all services before doing backup. Otherwise the 
    resulting file cannot be restored.

Backup
^^^^^^

Stop all services before you begin:

.. code-block::

    $ docker-compose stop
    Stopping ngwdocker_app_1           ... done
    Stopping ngwdocker_postgres_1      ... done

And make sure that there are no active containers - state of all
containers must be ``Exit``:

.. code-block::

    $ docker-compose ps
            Name                    Command                 State     Ports
    -----------------------------------------------------------------------
    ngwdocker_app_1       /opt/ngw/bin/docker-entryp ...   Exit 137
    ngwdocker_postgres_1  docker-entrypoint postgres       Exit 0

Now create backup with default filename:

.. code-block::

    $ docker-compose run --rm archivist backup
    backup/archivist-20200217-230615.tar.zst

In case backup directory is mounted as bind mount (not as docker volume)
resulting file is located under ``backup/`` directory. You can use scp or any
other utility upload file to another host:

.. code-block::

    $ scp backup/archivist-20200217-230615.tar.zst example.com:/remote/directory


In case of docker volume you can also copy this file to another host via ``ssh``
or any other tool such as ``s3cmd put``:

.. code-block::

    $ docker-compose run --rm archivist cat backup/archivist-20200217-230615.tar.zst | \
    > ssh user@example.com 'cat > archivist-20200217-230615.tar.zst'


Start all services again:

.. code-block::

    $ docker-compose start

Restore
^^^^^^^

Stop all services before you begin:

.. code-block::

    $ docker-compose stop

Restore archive:

.. code-block::

    $ docker-compose run --rm archivist restore backup/archivist-20200217-230615.tar.zst

Start all services again:

.. code-block::

    $ docker-compose start

Online backups with nextgisweb
------------------------------

NextGIS Web also provides backup tool that can be used online without stopping
services. Further information on this tool is available in the NextGIS Web
documentation. Aspects specific to NextGIS Web Docker are listed below.

Backup
^^^^^^

To create a backup with default filename, run the command:

.. code-block::

    $ docker-compose run --rm app nextgisweb backup
    ( A lot of debug messages here )
    backup/nextgisweb-20200220-164818.ngwbackup

In case backup directory is mounted as bind mount (not as docker volume)
resulting file is located under ``backup/`` directory. You can use ``scp`` or
any other utility upload file to another host:

.. code-block::

    $ scp backup/nextgisweb-20200220-164818.ngwbackup example.com:/remote/directory

Restore
^^^^^^^
Stop all services before you begin:

.. code-block::

    $ docker-compose stop

Restore archive:

.. code-block::

    $ docker-compose run --rm app nextgisweb restore FILENAME

Start all services again:

.. code-block::

    $ docker-compose start

