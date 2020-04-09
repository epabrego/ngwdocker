from setuptools import setup, find_packages

setup(
    name="ngwdocker",
    version="2.0.0.dev4",
    packages=find_packages(),
    python_requires=">=3.6",
    install_requires=[
        "packaging",
        "pyyaml",
        "click",
        "zope.event",
        "loguru",
        "bump2version",
    ],

    entry_points={
        "console_scripts": [
            "ngwdocker=ngwdocker.script:main",
        ],
    },

    zip_safe=False,
    package_data={
        "ngwdocker.base": [
            "image/*",
            "image/*/*",
            "image/*/*/*",
            "image/*/*/*/*",
        ],
        "ngwdocker": [
            "archivist/setup.py",
            "archivist/setup.cfg",
            "archivist/archivist/*.py",
        ]
    },
)
