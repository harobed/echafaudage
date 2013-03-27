import os, re

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

v = open(os.path.join(here, 'echafauder', '__init__.py'))
version = re.compile(r".*__version__ = '(.*?)'", re.S).match(v.read()).group(1)
v.close()

setup(
    name='echafauder',
    version=version,
    author='Stephane Klein',
    author_email='contact@stephane-klein.info',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    entry_points="""\
    [console_scripts]
    echafauder = echafauder.main:main
    """
)
