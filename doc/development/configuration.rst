Configuration file ``ngwdocker.yaml``
=====================================

Executable ``ngwdocker`` search for configuration file ``ngwdocker.yaml`` in
current directory. Example configuration file with some comments are listed
below.

.. code-block:: yaml

    # By default 'development' mode is used. To enable
    # production mode uncomment line below.
    # mode: production

    # Enable expirimental Python 3 support.
    # python3: true

    # By default ngwdocker scans package/ directory for
    # packages and each directory threared as package.
    # To disable this behaivor use `autoload` option.
    # autoload: false
    
    # Package specific configuration
    package:

      ngwdocker:
        # Enable pgadmin service for development.
        # pgadmin: { enabled: true }

        # Enable elasticsearch and kibana services.
        # elasticsearch: { enabled: true }
        # kibana: { enabled: true }

      # Do not forget this key when autoload disabled.
      nextgisweb:

      nextgisweb_qgis:
        # Temporary disable nextgisweb_qgis package.
        # enabled: false

      # Another way to temporary disable package.
      # nextgisweb_mapserver: false
