Requirements and installation
=============================

Requirements
------------

* Docker Engine >= 19.03
* Docker Compose >= 1.14
* Python >= 3.6
* Git >= 2.17

Ubuntu
^^^^^^

* `Docker Community Edition <https://docs.docker.com/install/linux/docker-ce/ubuntu/>`_ installation instructions
* `Docker Compose <https://docs.docker.com/compose/install/>`_  installation instructions

MacOS
^^^^^

.. note::

    NextGIS Web Docker on MacOS should be used only for development
    and testing purposes.

* `Docker Desktop for Mac`_ (includes Docker + ``/bin`` Engine and Docker Compose)

We recommend using `Brew`_ to install modern version of Git:

.. code-block:: shell

    $ brew install git

.. _Docker Desktop for Mac: https://docs.docker.com/docker-for-mac/install/
.. _Brew: https://brew.sh/


Windows
^^^^^^^

.. note::

    NextGIS Web Docker on Windows should be used only for development and
    testing purposes.

.. note::

    Developing nextgisweb using ngwdocker requires enabling a number of features
    that are disabled by default in Windows. Instructions for enabling them are
    given below. Pay attention to the newlines setting (CR/LF) and the symlinks
    in git.


Docker
""""""

Use `Docker Desktop for Windows`_ wich includes Docker Engine, Docker Compose,
Kubernetes ans some other tools.

* Docker Desktop for Windows uses Hyper-V which can't be used together with
  VirtualBox.

* Hyper-V available only on Windows Professional or Enterprise editions and
  not available on Windows Home Edition.

* Hyper-V should be enabled before Docker Desktop for Windows installation
  - see `Hyper-V instructions`_.

* After install, select a working drive in options (will ask current user
  password).

* Do not log into Docker Account.

Alternatively you can use `Docker Toolbox for Windows`_ wich is legacy and less
convenient solution. It uses Oracle VitrualBox and can run on 64-bit Windows 7
and higher.

* Working directory should be located under ``C:\Users`` folder. Only folders
  under ``C:\Users`` allowed to be mounted as docker local volume.

* Port forwarding use ``192.168.99.100`` by default instead of ``localhost``,
  so use ``http://192.168.99.100:8080`` instead of ``http://localhost:8080`` in
  instructions below.

.. _Docker Desktop for Windows: https://docs.docker.com/docker-for-windows/install/
.. _Hyper-V instructions: https://docs.microsoft.com/ru-ru/virtualization/hyper-v-on-windows/quick-start/enable-hyper-v
.. _Docker Toolbox for Windows: https://docs.docker.com/toolbox/toolbox_install_windows/

Python
""""""

Use latest Python 3 release from `Python Releases for Windows`_ and then
install required packages via PowerShell.

.. _Python Releases for Windows: https://www.python.org/downloads/windows/

Git
"""

Install latest version `Git for Windows`_. Two options are required:

* Symlinks support: ``core.symlinks=true``. Symlinks support requires
  additional permissions for non-administrator user - see `symlinks
  instructions on GitHub`_.

* Disable CR/LF conversions: ``core.autocrlf=input``.

Both options can be configured during install or during
``git clone``. You can check effective values using PowerShell outside of
any git repository:

.. code-block::

    PS D:\> git config --get core.symlinks
    true
    PS D:\> git config --get core.autocrlf
    input

If option doesn't match expected value add to ``git clone`` options for **each
repository below**:

.. code-block::

    PS D:\> git clone -c core.symlinks=true -c core.autocrlf=input git@github.com:nextgis/ngwdocker.git


.. _Git for Windows: https://git-scm.com/download/win
.. _Symlinks instructions on GitHub: https://github.com/git-for-windows/git/wiki/Symbolic-Links


Installation
------------

Check that Docker installed and configured correctly:

.. code-block:: shell

    $ docker run hello-world
    Hello from Docker!
    ...(snipped)...

Install `ngwdocker` package using one of the following methods:

**Method A:** Into current user profile:

.. code-block:: shell

    $ python3 -m pip install --user git+ssh://git@github.com/nextgis/ngwdocker.git
    # Executable ngwdocker now located in python user directory. Binary
    # directory location may vary on installation or platform. It can
    # obtained with "echo $(python3 -m site --user-base)/bin" command.
    # It can be added to PATH environment variable like this:
    $ export PATH=$(python3 -m site --user-base)/bin:$PATH
    $ mkdir ngwdocker
    $ cd ngwdocker

**Method B:** Into virtualenv (or any other virtualenv wrapper):

.. code-block:: shell

    $ mkdir ngwdocker
    $ cd ngwdocker
    $ python3 -m venv env
    $ . env/bin/activate
    $ pip install git+ssh://git@github.com/nextgis/ngwdocker.git
    # Executable ngwdocker is located in env/bin directory which
    # added to PATH variable during virtualenv activation.

**Method C:** Into virtualenv in editable mode for development purposes:

.. code-block:: shell

    $ git clone git@github.com:nextgis/ngwdocker.git
    $ cd ngwdocker
    $ python3 -m venv env
    $ . env/bin/activate
    $ pip install -e ./

Install nextgisweb package sources to package directory:

.. code-block:: shell

    $ mkdir -p package
    $ git clone git@github.com:nextgis/nextgisweb.git package/nextgisweb
    $ git clone git@github.com:nextgis/nextgisweb_qgis.git package/nextgisweb_qgis
    $ git clone git@github.com:nextgis/nextgisweb_mapserver.git package/nextgisweb_mapserver

Generate docker and docker-compose files, build container images and run web
main application container:

.. code-block:: shell

    $ ngwdocker
    2020-02-04 19:38:42.942 | WARNING  | ngwdocker.context:from_file:44 - File 'ngwdocker.yaml' not found! Using default configuration.
    2020-02-04 19:38:42.943 | DEBUG    | ngwdocker.context:load_packages:89 - Loading <module 'nextgisweb.docker' from 'package/nextgisweb/docker.py'>
    2020-02-04 19:38:42.943 | DEBUG    | ngwdocker.context:load_packages:89 - Loading <module 'nextgisweb_mapserver.docker' from 'package/nextgisweb_mapserver/docker.py'>
    2020-02-04 19:38:42.944 | DEBUG    | ngwdocker.context:load_packages:89 - Loading <module 'nextgisweb_qgis.docker' from 'package/nextgisweb_qgis/docker.py'>
    $ docker-compose build
    $ docker-compose up app
    Creating network "ngwdocker_default" with the default driver
    Creating volume "ngwdocker_data" with default driver
    Creating volume "ngwdocker_postgres" with default driver
    Creating ngwdocker_postgres_1 ... done
    Creating ngwdocker_app_1      ... done
    ( A lot of log messages )

If everything is OK go to http://localhost:8080 where you should see NextGIS Web
interface. Default administrator user is ``administrator`` with password ``admin``.
