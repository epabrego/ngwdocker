Typical image layout
====================

.. code-block:: shell

    /opt/ngw ($NGWROOT)
    │
    ├── data            # Data root directory: all container data
    │   ├── app         # stored in this directory and each service
    │   └── postgres    # uses own subdirectory wich is mounted as
    │                   # volume.
    │
    ├── config          # Volume for configuration files. In
    │   ├── app         # development mode it is mapped to docker 
    │   └── postgres    # host via bind. Each service used own
    │                   # subdirectory.
    │
    ├── secret          # Volume where secrets shared between
    │                   # containers such as postgres database
    │                   # password.
    │
    ├── backup          # Default location for backup files. See
    │                   # backup and restore section for details.
    │
    ├── bin             # Container specific binary files including
    │                   # docker-entrypoint.
    │
    ├── env             # Virtualenv root directory including bin/
    │                   # where nextgisweb executable located.
    │
    └── package         # Package sources directory. In development
        └── nextgisweb  # mode its mapped to docker host via bind.
