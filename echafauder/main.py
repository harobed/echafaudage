# -*- coding: utf8 -*-
# @:adhoc_run_time:@
usage = """echafauder

Usage:
    echafauder [options] -s <scaffolding> [<TARGET>]

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

    $ echafauder -s /path/to/directory/

    or

    $ echafauder -s my_scaffolding.tar.gz

    or

    $ echafauder -s http://example.com/my_scaffolding.tar.gz
"""

import os
import sys
import urlparse
import urllib
import tempfile
import shutil
import zipfile
import tarfile

try:
    # this raw_input is not converted by 2to3
    term_input = raw_input
except NameError:
    term_input = input

import json
from docopt import docopt  # @:adhoc:@
import echafauder.tempita  # @:adhoc:@


def copy_dir(source, dest, vars=None):
    if vars is None:
        vars = {}

    if os.path.isfile(dest):
        print('Error: %s is a file and not a folder' % dest)
        sys.exit(1)

    if not os.path.exists(dest):
        os.makedirs(dest)

    names = sorted(os.listdir(source))
    for name in names:
        if name in ('scaffolding.json', '.git', '.hg'):
            continue

        full_src = os.path.join(source, name)
        full_dest = os.path.join(dest, echafauder.tempita.sub(name, **vars))

        if os.path.isfile(full_src):
            if name.endswith('.tmpl'):
                full_dest = full_dest[:-len('.tmpl')]
                f = open(full_src, 'rb')
                content = f.read()
                f.close()

                f = open(full_dest, 'wb')
                f.write(
                    echafauder.tempita.sub(content, **vars)
                )
                f.close()
            else:
                shutil.copy(
                    full_src,
                    full_dest
                )

        if os.path.isdir(full_src):
            copy_dir(
                full_src,
                full_dest,
                vars
            )


def main():
    arguments = docopt(usage)
    if arguments['<TARGET>'] is None:
        arguments['<TARGET>'] = '.'

    if os.path.isfile(arguments['<TARGET>']):
        print('Error: %s is a file and not a folder' % arguments['<TARGET>'])
        sys.exit(1)

    scaffolding_source = arguments['--scaffolding']

    tmp_dir = None

    if not os.path.isdir(scaffolding_source):
        archive_type = None
        for ext in ('.zip', '.tar.gz'):
            if scaffolding_source.endswith(ext):
                archive_type = ext
                break

        if archive_type is None:
            print('%s file format not supported (scaffolding-engine support .zip and .tar.gz format)' % scaffolding_source)
            sys.exit(1)

        if (
            scaffolding_source.startswith('http://') or
            scaffolding_source.startswith('https://')
        ):
            tmp_dir = tempfile.mkdtemp()
            archive_path = os.path.join(
                tmp_dir,
                os.path.basename(urlparse.urlparse(scaffolding_source).path)
            )
            urllib.urlretrieve(scaffolding_source, archive_path)
        else:
            if not os.path.exists(scaffolding_source):
                print("%s folder not found" % scaffolding_source)
                sys.exit(1)

            tmp_dir = tempfile.mkdtemp()
            archive_path = scaffolding_source

        if archive_type == '.zip':
            archive_file = zipfile.ZipFile(archive_path)
        elif archive_type == '.tar.gz':
            archive_file = tarfile.open(archive_path)

        archive_file.extractall(os.path.join(tmp_dir, 'content'))
        archive_file.close()

        if archive_type == '.tar.gz':
            scaffolding_source = os.path.join(tmp_dir, 'content')
        elif archive_type == '.zip':
            scaffolding_source = os.path.join(
                tmp_dir,
                'content',
                os.listdir(os.path.join(tmp_dir, 'content'))[0]
            )

    vars = {}
    if arguments['--vars']:
        for item in arguments['--vars'].split(','):
            k, v = item.split('=')
            vars[k] = v

    json_data = None
    scaffolding_json = os.path.join(scaffolding_source, 'scaffolding.json')
    if os.path.exists(scaffolding_json):
        with open(scaffolding_json, 'r') as f:
            json_data = json.load(f)
            if 'variables' in json_data:
                for k, v in json_data['variables'].items():
                    if k not in vars:
                        if isinstance(v, dict):
                            if 'default' in v:
                                vars[k] = v['default']
                        else:
                            vars[k] = None

    for k, v in vars.items():
        if v is None:
            x = term_input('%s : ' % k)
            vars[k] = x

    if json_data and ('variables' in json_data):
        for k, v in json_data['variables'].items():
            if isinstance(v, dict) and ('lambda' in v):
                exec("""f = lambda vars: %s""" % v['lambda'])
                vars[k] = f(vars)

    copy_dir(
        source=scaffolding_source,
        dest=arguments['<TARGET>'],
        vars=vars
    )
    if tmp_dir:
        shutil.rmtree(tmp_dir)

if __name__ == '__main__':
    main()