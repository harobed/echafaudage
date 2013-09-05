import virtualenv, textwrap

output = virtualenv.create_bootstrap_script(textwrap.dedent("""
import os, subprocess, tempfile
from shutil import rmtree

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen  # NOQA

def adjust_options(options, args):
    global tmp_dir

    tmp_dir = tempfile.mkdtemp()
    print('download setuptools...')
    f = open(os.path.join(tmp_dir, 'setuptools-latest.tar.gz'), 'w')
    f.write(urlopen('https://pypi.python.org/packages/source/s/setuptools/setuptools-1.1.1.tar.gz').read())
    f.close()
    print('setuptools downloaded')

    print('download pip...')
    f = open(os.path.join(tmp_dir, 'pip-latest.tar.gz'), 'w')
    f.write(urlopen('https://github.com/pypa/virtualenv/blob/develop/virtualenv_support/pip-1.4.1.tar.gz?raw=true').read())
    f.close()
    print('pip downloaded')

    if len(args) == 0:
        options.search_dirs = [tmp_dir]
        args.append('.')

def after_install(options, home_dir):
    global tmp_dir

    rmtree(tmp_dir)

    subprocess.call([
        os.path.join('bin', 'pip'),
        'install', '-r', 'devel-requirements.txt'
    ])

"""))
f = open('bootstrap.py', 'w').write(output)
