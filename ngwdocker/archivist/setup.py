from setuptools import setup, find_packages

setup(
    name="archivist",
    version="2.0.0.dev4",
    packages=find_packages(),
    install_requires=[
        "click",
        "pathlib; python_version < '3.4'",
    ],

    entry_points={
        "console_scripts": [
            "archivist = archivist:main",
            "backup = archivist:shortcut_backup",
            "restore = archivist:shortcut_restore",
        ],
    },

    zip_safe=False,
)
