import os, re

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'docs/index.rst')).read()

v = open(os.path.join(here, 'echafaudage', '__init__.py'))
version = re.compile(r".*__version__ = '(.*?)'", re.S).match(v.read()).group(1)
v.close()

setup(
    name='echafaudage',
    description='A lighting scaffolding python tool without dependencies',
    version=version,
    author='Stephane Klein',
    author_email='contact@stephane-klein.info',
    long_description=README,
    url='http://harobed.github.io/echafaudage/',
    license='BSD License',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2.6',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License'
    ],
    include_package_data=True,
    zip_safe=False,
    entry_points="""\
    [console_scripts]
    echafaudage = echafaudage.main:main
    """
)
