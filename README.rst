Quick start
===========

::

    $ python -c "$(curl -fsSL https://raw.github.com/harobed/echafaudage/master/echafauder.py)" -s https://github.com/harobed/python_package_scaffolding/archive/master.zip /tmp/my_new_project
    mail : contact@stephane-klein.info
    version : 0.1.0
    package_name : my-project
    author : Stéphane Klein

Now your project is in ``/tmp/my_new_project/``

::

    $ ls /tmp/my_new_project/
    bootstrap.py  devel-requirements.txt  my_project  requirements.txt  setup.py  tests  unittest.cfg


You can also install "echafauder" on your system
================================================

::

    $ pip install https://github.com/harobed/echafaudage/archive/master.zip
  
And use ``echafauder`` like this :

::

    $ echafauder -s https://github.com/harobed/python_package_scaffolding/archive/master.zip /tmp/my_new_project


See also
========

If you want more powered scaffolding tool, you can look at `mr.bob <http://mrbob.readthedocs.org/en/latest/index.html>`_.
