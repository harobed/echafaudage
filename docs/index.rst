===========
Echafaudage
===========

.. raw:: html

   <p id="subtitle"><strong>A scaffolding python tool without dependencies</strong></p>

Features :

* erect and create scaffolding easily
* no dependency
* standalone file executable directly with ``python -c "$(curl ...)"``

Use case :

* very short quick start project (you need install nothing except python)


Example of use
==============

You can directly erect scaffolding **without installing nothing on your system**.

Example, if you want erect `Python package scaffolding <https://github.com/harobed/python_package_scaffolding>`_ 
scaffolding then **Paste that at a Terminal prompt** :

::

    $ python -c "$(curl -fsSL https://raw.github.com/harobed/echafaudage/master/echafaudage.py)" -s https://github.com/harobed/python_package_scaffolding/archive/master.zip /tmp/my_new_project


Next *echafaudage* ask some questions :

::

    mail : contact@stephane-klein.info
    version : 0.1.0
    package_name : my-project
    author : Stéphane Klein

Now your project is in ``/tmp/my_new_project/``

::

    $ ls /tmp/my_new_project/
    bootstrap.py  devel-requirements.txt  my_project  requirements.txt  setup.py  tests  unittest.cfg


You can also install "echafaudage" on your system
==================================================

::

    $ pip install echafaudage
  
And use ``echafaudage`` like this :

::

    $ echafaudage -s https://github.com/harobed/python_package_scaffolding/archive/master.zip /tmp/my_new_project

You can also directly set some variable in command line :

::

    $ echafaudage -s https://github.com/harobed/python_package_scaffolding/archive/master.zip /tmp/my_new_project --vars project_name=my-project,version=1.0


echafaudage usage
=================

::

    $ bin/echafaudage --help
    Usage: echafaudage [options] -s <scaffolding> [<TARGET>]

    Arguments:
        TARGET where scaffolding will be created, by default it is "." (current directory)


    Options:
        -s, --scaffolding=<scaffolding> The scaffolding to use, can be a directory path,
                                        an archive or archive url.
        --vars=<variables>              Custom variables, e.g --vars hello=world,sky=blue
        -h --help                       Show this screen.
        -v, --verbose
        --version


    Example:

        $ echafaudage -s /path/to/directory/

        or

        $ echafaudage -s my_scaffolding.tar.gz

        or

        $ echafaudage -s http://example.com/my_scaffolding.tar.gz


How to create new scaffolding
=============================

First, you can see `Python package scaffolding <https://github.com/harobed/python_package_scaffolding>`_ 
scaffolding example.

In this repository : 

::

    .
    ├── README.rst
    ├── bootstrap.py
    ├── devel-requirements.txt
    ├── requirements.txt
    ├── scaffolding.json               <= scaffolding configuration file
    ├── setup.py.tmpl                  <= template file
    ├── tests
    │   └── test_basic.py
    ├── unittest.cfg
    └── {{package_name_underscore}}    <= this folder is renamed with "package_name_underscore" variable value
        └── __init__.py.tmpl           <= template file

``{{package_name_underscore}}/__init__.py.tmpl`` content :

::

    __version__ = '{{version}}'

| The file with ``.tmpl`` extension are templates files.
| Template file are parsed by `tempita <http://pythonpaste.org/tempita/>`_ template engine with variables
  pass to *echafaudage*.
| The ``.tmpl`` extension is stripped in target folder.

The ``scaffolding.json`` (json format) configure the variable list :

::

    {
        "variables": {
            "package_name": null,
            "author": null,
            "mail": null,
            "package_name_underscore": {
                "lambda": "vars['package_name'].replace('-', '_')"
            },
            "version": {
                "default": "0.1.0"
            }
        },
        "ignores": [
            "README.rst"
        ]
    }

* "variables" is dict with the list of variables
* "ignores" is a list with the list of file to ignore

See also
========

If you want more powered scaffolding tool, you can look at `mr.bob <http://mrbob.readthedocs.org/en/latest/index.html>`_.

More information about Python Skeleton Builder Tools see this wiki page : https://wiki.python.org/moin/SkeletonBuilderTools
