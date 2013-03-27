Example of use
==============

You can directly erect scaffolding without installing nothing on your system :

::

    $ python -c "$(curl -fsSL https://raw.github.com/harobed/echafaudage/master/echafaudage.py)" -s https://github.com/harobed/python_package_scaffolding/archive/master.zip /tmp/my_new_project

or more shortly :

::

    $ python -c "$(curl -fsSL http://git.io/PT9OkQ)" -s https://github.com/harobed/python_package_scaffolding/archive/master.zip /tmp/my_new_project

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

    $ pip install https://github.com/harobed/echafaudage/archive/master.zip
  
And use ``echafaudage`` like this :

::

    $ echafaudage -s https://github.com/harobed/python_package_scaffolding/archive/master.zip /tmp/my_new_project

You can also directly set some variable in command line :

::

    $ echafaudage -s https://github.com/harobed/python_package_scaffolding/archive/master.zip /tmp/my_new_project --vars project_name=my-project,version=1.0


See also
========

If you want more powered scaffolding tool, you can look at `mr.bob <http://mrbob.readthedocs.org/en/latest/index.html>`_.
