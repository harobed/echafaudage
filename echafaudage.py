# -*- coding: utf8 -*-
# @:adhoc_run_time:@
# @:adhoc_remove:@
# @:adhoc_run_time_engine:@
# -*- coding: utf-8 -*-
# @:adhoc_compiled:@ 2013-03-28 00:37:36.331567
import sys
import os
import re

try:
    from cStringIO import StringIO as _AdHocBytesIO, StringIO as _AdHocStringIO
except ImportError:
    from io import BytesIO as _AdHocBytesIO, StringIO as _AdHocStringIO

class RtAdHoc(object):                                     # |||:cls:|||
    line_delimiters = ('@:', ':@')
    section_delimiters = ('@:', ':@')

    template_process_hooks = {}
    extra_templates = []

    export_dir = '__adhoc__'
    extract_dir = '.'
    flat = True
    forced = False

    frozen = False

    quiet = False
    verbose = False
    debug = False

    include_path = []
    export_need_init = {}
    export_have_init = {}
    extract_warn = False

    def _adhoc_string_util():
        def isstring(obj):
            return isinstance(obj, basestring)
        try:
            isstring("")
        except NameError:
            def isstring(obj):
                return isinstance(obj, str) or isinstance(obj, bytes)
        def _uc(string):
            return unicode(string, 'utf-8')
        try:
            _uc("")
        except NameError:
            _uc = lambda x: x
        uc_type = type(_uc(""))
        def uc(value):
            if isstring(value) and not isinstance(value, uc_type):
                return _uc(value)
            return value
        return staticmethod(isstring), uc_type, staticmethod(uc)

    isstring, uc_type, uc = _adhoc_string_util()

    @staticmethod
    def adhoc_tag(symbol_or_re, delimiters, is_re=False):    # |:fnc:|
        ldlm = delimiters[0]
        rdlm = delimiters[1]
        if is_re:
            ldlm = re.escape(ldlm)
            rdlm = re.escape(rdlm)
        return ''.join((ldlm, symbol_or_re, rdlm))

    @classmethod
    def tag_split(cls, string, tag, is_re=False):            # |:fnc:|
        if not is_re:
            tag = re.escape(tag)
        ro = re.compile(''.join(('^[^\n]*(', tag, ')[^\n]*$')), re.M)
        result = []
        last_end = 0
        string = cls.decode_source(string)
        for mo in re.finditer(ro, string):
            start = mo.start(0)
            end = mo.end(0)
            result.append((False, string[last_end:start]))
            result.append((True, string[start:end+1]))
            last_end = end+1
        result.append((False, string[last_end:]))
        return result

    @classmethod
    def adhoc_parse_line(cls, tagged_line, symbol_or_re=None, # |:clm:|
                         delimiters=None, is_re=False, strip_comment=None):
        if delimiters is None:
            delimiters = cls.line_delimiters
        if symbol_or_re is None:
            dlm = delimiters[1]
            if dlm:
                symbol_or_re = ''.join(('[^', dlm[0], ']+'))
            else:
                symbol_or_re = ''.join(('[^\\s]+'))
            is_re = True
        if not is_re:
            symbol_or_re = re.escape(symbol_or_re)
        tag_rx = cls.adhoc_tag(''.join(('(', symbol_or_re, ')')), delimiters, is_re=True)
        mo = re.search(tag_rx, tagged_line)
        if mo:
            ptag = mo.group(1)
        else:
            ptag = ''
        strip_rx = ''.join(('^.*', tag_rx, '\\s*'))
        tag_arg = re.sub(strip_rx, '', tagged_line).strip()
        if strip_comment:
            tag_arg = re.sub('\\s*#.*', '', tag_arg)
        return (ptag, tag_arg)

    @classmethod
    def set_delimiters(cls, line_delimiters=None, section_delimiters=None): # |:clm:|
        delimiter_state = (cls.line_delimiters, cls.section_delimiters)
        if line_delimiters is None:
            line_delimiters = delimiter_state[0]
            if section_delimiters is None:
                section_delimiters = delimiter_state[1]
        elif section_delimiters is None:
            section_delimiters = line_delimiters
        cls.line_delimiters, cls.section_delimiters = (
            line_delimiters, section_delimiters)
        return delimiter_state

    @classmethod
    def reset_delimiters(cls, delimiter_state):              # |:clm:|
        cls.line_delimiters, cls.section_delimiters = delimiter_state

    @classmethod
    def inc_delimiters(cls):                                 # |:clm:|

        inc_first = lambda dlm: (((not dlm) and ('')) or (dlm[0] + dlm))
        inc_last = lambda dlm: (((not dlm) and ('')) or (dlm + dlm[-1]))
        outer_delimiters = [(inc_first(dlm[0]), inc_last(dlm[1]))
                            for dlm in (cls.line_delimiters,
                                        cls.section_delimiters)]
        return cls.set_delimiters(*outer_delimiters)

    @classmethod
    def line_tag(cls, symbol_or_re, is_re=False):            # |:clm:|
        return cls.adhoc_tag(symbol_or_re, cls.line_delimiters, is_re)

    @classmethod
    def section_tag(cls, symbol_or_re, is_re=False):         # |:clm:|
        return cls.adhoc_tag(symbol_or_re, cls.section_delimiters, is_re)

    @classmethod
    def tag_lines(cls, string, tag, is_re=False):            # |:clm:|
        result = []
        for section in cls.tag_split(string, tag, is_re):
            if section[0]:
                result.append(section[1])
        return result

    @classmethod
    def tag_partition(cls, string, tag, is_re=False, headline=False): # |:clm:|
        in_section = False
        body_parts = []
        sections = []
        tagged_line = ''
        for section in cls.tag_split(string, tag, is_re):
            if section[0]:
                in_section = not in_section
                tagged_line = section[1]
                continue
            if in_section:
                if headline:
                    sections.append((tagged_line, section[1]))
                else:
                    sections.append(section[1])
            else:
                body_parts.append(section[1])
        return body_parts, sections

    @classmethod
    def tag_sections(cls, string, tag, is_re=False, headline=False): # |:clm:|
        body_parts, sections = cls.tag_partition(string, tag, is_re, headline)
        return sections

    @classmethod
    def line_tag_parse(cls, tagged_line, symbol_or_re=None, is_re=False, # |:clm:|
                       strip_comment=None):
        return cls.adhoc_parse_line(tagged_line, symbol_or_re, cls.line_delimiters,
                                    is_re, strip_comment=strip_comment)

    @classmethod
    def line_tag_strip(cls, tagged_line, symbol_or_re=None, is_re=False, # |:clm:|
                       strip_comment=None):
        return cls.line_tag_parse(tagged_line, symbol_or_re, is_re, strip_comment)[1]

    @classmethod
    def section_tag_parse(cls, tagged_line, symbol_or_re=None, is_re=False, # |:clm:|
                       strip_comment=None):
        return cls.adhoc_parse_line(tagged_line, symbol_or_re, cls.section_delimiters,
                                    is_re, strip_comment=strip_comment)

    @classmethod
    def section_tag_strip(cls, tagged_line, symbol_or_re=None, is_re=False, # |:clm:|
                       strip_comment=None):
        return cls.section_tag_parse(tagged_line, symbol_or_re, is_re, strip_comment)[1]

    @classmethod
    def transform_lines(cls, transform, string,              # |:clm:|
                        symbol_or_re, is_re=False, delimiters=None):
        if delimiters is None:
            delimiters = cls.line_delimiters
        result = []
        in_section = False
        for section in cls.tag_split(
            string, cls.adhoc_tag(symbol_or_re, delimiters, is_re), is_re):
            blob = section[1]
            if section[0]:
                in_section = not in_section
                blob = transform(blob)
            result.append(blob)
        string = ''.join(result)
        return string

    @classmethod
    def transform_sections(cls, transform, string,           # |:clm:|
                           symbol_or_re, is_re=False):
        result = []
        in_section = False
        headline = ''
        for section in cls.tag_split(
            string, cls.section_tag(symbol_or_re, is_re), is_re):
            blob = section[1]
            if section[0]:
                in_section = not in_section
                if in_section:
                    headline = blob
                    continue
            elif in_section:
                blob, headline = transform(blob, headline)
                result.append(headline)
            result.append(blob)
        string = ''.join(result)
        return string

    @classmethod
    def line_tag_rename(cls, string, symbol_or_re, renamed, is_re=False, delimiters=None): # |:clm:|
        if is_re:
            transform = lambda blob: re.sub(symbol_or_re, renamed, blob)
        else:
            transform = lambda blob: blob.replace(symbol_or_re, renamed)
        return cls.transform_lines(transform, string, symbol_or_re, is_re, delimiters)

    @classmethod
    def line_tag_remove(cls, string, symbol_or_re, is_re=False, delimiters=None): # |:clm:|
        transform = lambda blob: ''
        return cls.transform_lines(transform, string, symbol_or_re, is_re, delimiters)

    @classmethod
    def section_tag_rename(cls, string, symbol_or_re, renamed, is_re=False): # |:clm:|
        if is_re:
            transform = lambda blob: re.sub(symbol_or_re, renamed, blob)
        else:
            transform = lambda blob: blob.replace(symbol_or_re, renamed)
        return cls.transform_lines(transform, string, symbol_or_re, is_re, cls.section_delimiters)

    @classmethod
    def section_tag_remove(cls, string, symbol_or_re, is_re=False): # |:clm:|
        transform = lambda blob: ''
        return cls.transform_lines(transform, string, symbol_or_re, is_re, cls.section_delimiters)

    @classmethod
    def indent_sections(cls, string, symbol_or_re, is_re=False): # |:clm:|
        result = []
        in_section = False
        indent = 0
        for section in cls.tag_split(
            string, cls.section_tag(symbol_or_re, is_re), is_re):
            blob = section[1]
            if section[0]:
                in_section = not in_section
                if in_section:
                    tag_arg = cls.section_tag_strip(blob)
                    if tag_arg:
                        indent = int(tag_arg)
                    else:
                        indent = -4
            else:
                if in_section and indent:
                    if indent < 0:
                        rx = re.compile(''.join(('^', ' ' * (-indent))), re.M)
                        blob = rx.sub('', blob)
                    elif indent > 0:
                        rx = re.compile('^', re.M)
                        blob = rx.sub(' ' * indent, blob)
                    indent = 0
            result.append(blob)
        string = ''.join(result)
        return string

    @classmethod
    def enable_sections(cls, string, symbol_or_re, is_re=False): # |:clm:|
        enable_ro = re.compile('^([ \t\r]*)(# ?)', re.M)
        enable_sub = '\\1'
        transform = lambda blob, hl: (enable_ro.sub(enable_sub, blob), hl)
        return cls.transform_sections(transform, string, symbol_or_re, is_re)

    adhoc_rx_tab_check = re.compile('^([ ]*\t)', re.M)
    adhoc_rx_disable_simple = re.compile('^', re.M)
    adhoc_rx_min_indent_check = re.compile('^([ ]*)([^ \t\r\n]|$)', re.M)

    @classmethod
    def disable_transform(cls, section, headline=None):      # |:clm:|
        if not section:
            return (section, headline)

        if cls.adhoc_rx_tab_check.search(section):
            # tabs are evil
            if cls.verbose:
                list(map(sys.stderr.write,
                         ('# dt: evil tabs: ', repr(section), '\n')))
            return (
                cls.adhoc_rx_disable_simple.sub(
                    '# ', section.rstrip()) + '\n',
                headline)

        min_indent = ''
        for mo in cls.adhoc_rx_min_indent_check.finditer(section):
            indent = mo.group(1)
            if indent:
                if (not min_indent or len(min_indent) > len(indent)):
                    min_indent = indent
            elif mo.group(2):
                min_indent = ''
                break
        adhoc_rx_min_indent = re.compile(
            ''.join(('^(', min_indent, '|)([^\n]*)$')), re.M)

        if section.endswith('\n'):
            section = section[:-1]
        dsection = []
        for mo in adhoc_rx_min_indent.finditer(section):
            indent = mo.group(1)
            rest = mo.group(2)
            if not indent and not rest:
                #leave blank lines blank
                dsection.append('\n')
            else:
                dsection.extend((indent, '# ', rest, '\n'))
        return (''.join(dsection), headline)

    @classmethod
    def disable_sections(cls, string, symbol_or_re, is_re=False): # |:clm:|
        return cls.transform_sections(
            cls.disable_transform, string, symbol_or_re, is_re)

    @classmethod
    def remove_sections(cls, string, symbol_or_re, is_re=False): # |:clm:|
        ah_retained, ah_removed = cls.tag_partition(
            string, cls.section_tag(symbol_or_re, is_re), is_re)
        return ''.join(ah_retained)

    @staticmethod
    def check_coding(source):                                # |:fnc:|
        if source:
            eol_seen = 0
            for c in source:
                if isinstance(c, int):
                    lt_ = lambda a, b: a < b
                    chr_ = lambda a: chr(a)
                else:
                    lt_ = lambda a, b: True
                    chr_ = lambda a: a
                break
            check = []
            for c in source:
                if lt_(c, 127):
                    check.append(chr_(c))
                if c == '\n':
                    eol_seen += 1
                    if eol_seen == 2:
                        break
            check = ''.join(check)
            mo = re.search('-[*]-.*coding:\\s*([^;\\s]+).*-[*]-', check)
        else:
            mo = None
        if mo:
            coding = mo.group(1)
        else:
            coding = 'utf-8'
        return coding

    @classmethod
    def decode_source(cls, source):                          # |:clm:|
        if not source:
            return cls.uc('')
        if not isinstance(source, cls.uc_type) and hasattr(source, 'decode'):
            source = source.decode(cls.check_coding(source))
        return source

    @classmethod
    def encode_source(cls, source):                          # |:clm:|
        if not source:
            return ''.encode('utf-8')
        if isinstance(source, cls.uc_type) and hasattr(source, 'encode'):
            source = source.encode(cls.check_coding(source))
        return source

    @classmethod
    def read_source(cls, file_, decode=True):                # |:clm:|
        source = None
        if not file_ or file_ == '-':
            # Python3 has a buffer attribute for binary input.
            if hasattr(sys.stdin, 'buffer'):
                source = sys.stdin.buffer.read()
            else:
                source = sys.stdin.read()
        else:
            try:
                sf = open(file_, 'rb')
                source = sf.read()
                sf.close()
            except IOError:
                for module in sys.modules.values():
                    if (module
                        and hasattr(module, '__file__')
                        and module.__file__ == file_):
                        if (hasattr(module, '__adhoc__')
                            and hasattr(module.__adhoc__, 'source')):
                            source = module.__adhoc__.source
                            break
        if source is None:
            raise IOError('source not found for `' + str(file_) + '`')
        if decode:
            return cls.decode_source(source)
        return source

    @classmethod
    def write_source(cls, file_, source, mtime=None, mode=None): # |:clm:|
        esource = cls.encode_source(source)
        if not file_ or file_ == '-':
            if hasattr(sys.stdout, 'buffer'):
                sys.stdout.buffer.write(esource)
            else:
                try:
                    sys.stdout.write(esource)
                except TypeError:
                    sys.stdout.write(source)
        else:
            sf = open(file_, 'wb')
            sf.write(esource)
            sf.close()
            if mode is not None:
                os.chmod(file_, mode)
            if mtime is not None:
                import datetime
                if cls.isstring(mtime):
                    try:
                        date, ms = mtime.split('.')
                    except ValueError:
                        date = mtime
                        ms = 0
                    mtime = cls.strptime(date, '%Y-%m-%dT%H:%M:%S')
                    mtime += datetime.timedelta(microseconds=int(ms))
                if isinstance(mtime, datetime.datetime):
                    ts = int(mtime.strftime("%s"))
                else:
                    ts = mtime
                os.utime(file_, (ts, ts))

    @classmethod
    def check_xfile(cls, file_, xdir=None):                  # |:clm:|
        if xdir is None:
            xdir = cls.extract_dir
        if not file_:
            file_ = '-'
        if file_ == '-':
            return file_
        file_ = os.path.expanduser(file_)
        if os.path.isabs(file_):
            xfile = file_
        else:
            xfile = os.path.join(xdir, file_)
        xfile = os.path.abspath(xfile)
        if os.path.exists(xfile):
            # do not overwrite files
            if (cls.extract_warn or (cls.verbose)) and not cls.quiet:
                list(map(sys.stderr.write, (
                    "# xf: ", cls.__name__, ": warning file `", file_,
                    "` exists. skipping ...\n")))
            return None
        xdir = os.path.dirname(xfile)
        if not os.path.exists(xdir):
            os.makedirs(xdir)
        return xfile

    @classmethod
    def pack_file(cls, source, zipped=True):                 # |:clm:|
        import base64, gzip
        if zipped:
            sio = _AdHocBytesIO()
            gzf = gzip.GzipFile('', 'wb', 9, sio)
            gzf.write(cls.encode_source(source))
            gzf.close()
            source = sio.getvalue()
            sio.close()
        else:
            source = cls.encode_source(source)
        source = base64.b64encode(source)
        source = source.decode('ascii')
        return source

    @classmethod
    def unpack_file(cls, source64, zipped=True, decode=True): # |:clm:|
        import base64, gzip
        source = source64.encode('ascii')
        source = base64.b64decode(source)
        if zipped:
            sio = _AdHocBytesIO(source)
            gzf = gzip.GzipFile('', 'rb', 9, sio)
            source = gzf.read()
            gzf.close()
            sio.close()
        if decode:
            source = cls.decode_source(source)
        return source

    @classmethod
    def unpack_(cls, mod_name=None, file_=None, mtime=None, # |:clm:||:api_fi:|
                mode=None, zipped=True, flat=None, source64=None):
        xfile = cls.check_xfile(file_, cls.extract_dir)
        if xfile is None:
            return
        if cls.verbose:
            list(map(sys.stderr.write,
                     ("# xf: ", cls.__name__, ": unpacking `", file_, "`\n")))
        source = cls.unpack_file(source64, zipped=zipped, decode=False)
        cls.write_source(xfile, source, mtime, mode)

    @classmethod
    def strptime(cls, date_string, format_):                 # |:clm:|
        import datetime
        if hasattr(datetime.datetime, 'strptime'):
            strptime_ = datetime.datetime.strptime
        else:
            import time
            strptime_ = lambda date_string, format_: (
                datetime.datetime(*(time.strptime(date_string, format_)[0:6])))
        return strptime_(date_string, format_)

    @classmethod
    def import_(cls, mod_name=None, file_=None, mtime=None, # |:clm:||:api_fi:|
                mode=None, zipped=True, flat=None, source64=None):
        import datetime
        import time

        module = cls.module_setup(mod_name)

        if mtime is None:
            mtime = datetime.datetime.fromtimestamp(0)
        else:
            # mtime=2011-11-23T18:04:26[.218506], zipped=True, flat=None, source64=
            try:
                date, ms = mtime.split('.')
            except ValueError:
                date = mtime
                ms = 0
            mtime = cls.strptime(date, '%Y-%m-%dT%H:%M:%S')
            mtime += datetime.timedelta(microseconds=int(ms))

        source = cls.unpack_file(source64, zipped=zipped, decode=False)

        mod_parts = mod_name.split('.')
        mod_child = mod_parts[-1]
        parent = '.'.join(mod_parts[:-1])
        old_mtime = module.__adhoc__.mtime
        module = cls.module_setup(mod_name, file_, mtime, source, mode)
        if len(parent) > 0:
            setattr(sys.modules[parent], mod_child, module)

        if module.__adhoc__.mtime != old_mtime:
            source = cls.encode_source(module.__adhoc__.source)
            exec(source, module.__dict__)

    @classmethod
    def module_setup(cls, module=None, file_=None, mtime=None, # |:clm:||:api_fi:|
                     source=None, mode=None):
        m = 'ms: '
        class Attr:                                          # |:cls:|
            pass

        import types, datetime, os
        if not isinstance(module, types.ModuleType):
            mod_name = module
            if mod_name is None:
                mod_name = __name__
            try:
                if mod_name not in sys.modules:
                    __import__(mod_name)
                module = sys.modules[mod_name]
            except (ImportError, KeyError):
                import imp
                module = imp.new_module(mod_name)
                sys.modules[mod_name] = module
        else:
            mod_name = module.__name__

        if mtime is None:
            if (file_ is not None
                or source is not None):
                # the info is marked as outdated
                mtime = datetime.datetime.fromtimestamp(1)
            else:
                # the info is marked as very outdated
                mtime = datetime.datetime.fromtimestamp(0)

        if not hasattr(module, '__adhoc__'):
            adhoc = Attr()
            setattr(module, '__adhoc__', adhoc)
            setattr(adhoc, '__module__', module)

            mtime_set = None
            mode_set = mode
            if hasattr(module, '__file__'):
                module_file = module.__file__
                if module_file.endswith('.pyc'):
                    module_file = module_file[:-1]
                if os.access(module_file, os.R_OK):
                    stat = os.stat(module_file)
                    mtime_set = datetime.datetime.fromtimestamp(
                        stat.st_mtime)
                    mode_set = stat.st_mode
            if mtime_set is None:
                # the info is marked as very outdated
                mtime_set = datetime.datetime.fromtimestamp(0)
            adhoc.mtime = mtime_set
            adhoc.mode = mode_set
        else:
            adhoc = module.__adhoc__

        if (mtime > adhoc.mtime
            or not hasattr(module, '__file__')):
            if file_ is not None:
                setattr(module, '__file__', file_)
                if os.access(file_, os.R_OK):             # |:api_fi:|
                    stat = os.stat(file_)
                    adhoc.mtime = datetime.datetime.fromtimestamp(
                        stat.st_mtime)
                    adhoc.mode = stat.st_mode
                    if adhoc.mtime > mtime:
                        # the file on disk is newer than the adhoc'ed source
                        try:
                            delattr(adhoc, 'source')
                        except AttributeError:
                            pass
                        source = None

        if (mtime > adhoc.mtime
            or not hasattr(adhoc, 'source')):
            if source is not None:
                adhoc.source = source
                adhoc.mtime = mtime
                adhoc.mode = mode

        if not hasattr(adhoc, 'source'):
            try:
                file_ = module.__file__
                file_, source = cls.std_source_param(file_, source)
                adhoc.source = source
            except (AttributeError, IOError):
                pass

        return module

    @classmethod
    def std_source_param(cls, file_=None, source=None): # |:clm:||:api_fi:|
        if file_ is None:
            file_ = __file__
        if file_.endswith('.pyc'):
            file_ = file_[:-1]
        if source is None:
            source = cls.read_source(file_)
        return (file_, source)

    @classmethod
    def export_source(cls, string, no_remove=False, no_disable=False): # |:clm:|
        string = cls.collapse_macros(string)
        if not no_remove:
            string = cls.remove_sections(string, 'adhoc_remove')
        string = cls.remove_sections(string, 'adhoc_import')
        string = cls.remove_sections(string, 'adhoc_unpack')
        string = cls.remove_sections(string, 'adhoc_template_v')
        if not no_disable:
            string = cls.enable_sections(string, 'adhoc_disable')
            string = cls.disable_sections(string, 'adhoc_enable')
        if not no_remove:
            string = cls.section_tag_rename(string, 'adhoc_remove_', 'adhoc_remove')
        return string

    @classmethod
    def unpack(cls, file_=None, source=None):                # |:clm:|
        file_, source = cls.std_source_param(file_, source)
        source_sections, unpack_sections = cls.tag_partition(
            source, cls.section_tag('adhoc_unpack'))
        sv_extract_warn = cls.extract_warn
        cls.extract_warn = True
        unpack_call = ''.join((cls.__name__, '.unpack_'))
        for unpack_section in unpack_sections:
            unpack_section = re.sub('^\\s+', '', unpack_section)
            unpack_section = re.sub(
                '^[^(]*(?s)', unpack_call, unpack_section)
            try:
                #RtAdHoc = cls # unpack_call takes care of this
                exec(unpack_section.lstrip(), globals(), locals())
            except IndentationError:
                sys.stderr.write("!!! IndentationError !!!\n")
        cls.extract_warn = sv_extract_warn

    @classmethod
    def extract(cls, file_=None, source=None):               # |:clm:|
        cls.unpack(file_, source)
        cls.extract_templates(file_, source, export=True)

    @classmethod
    def export__(cls, mod_name=None, file_=None, mtime=None, # |:clm:||:api_fi:|
                 mode=None, zipped=True, flat=None, source64=None):
        source = cls.unpack_file(source64, zipped=zipped, decode=False)
        if file_ is None:
            return
        file_base = os.path.basename(file_)
        if file_base.startswith('__init__.py'):
            is_init = True
        else:
            is_init = False

        parts = mod_name.split('.')
        base = parts.pop()
        if parts:
            module_dir = os.path.join(*parts)
            cls.export_need_init[module_dir] = True
        else:
            module_dir = ''
        if is_init:
            module_dir = os.path.join(module_dir, base)
            cls.export_have_init[module_dir] = True
        module_file = os.path.join(module_dir, file_base)

        cls.export_(source, module_file, mtime, mode, flat)

    @classmethod
    def export_(cls, source, file_, mtime, mode, flat=None): # |:clm:|
        cflat = cls.flat
        if flat is None:
            flat = cflat
        cls.flat = flat
        if not flat:
            # extract to export directory
            sv_extract_dir = cls.extract_dir
            cls.extract_dir = cls.export_dir
            cls.extract(file_, source)
            cls.extract_dir = sv_extract_dir

            source_sections, import_sections = cls.tag_partition(
                source, cls.section_tag('adhoc_import'))
            source = cls.export_source(''.join(source_sections))
            export_call = ''.join((cls.__name__, '.export__'))

            xfile = cls.check_xfile(file_, cls.export_dir)
            if xfile is not None:
                cls.write_source(xfile, source, mtime, mode)
                if cls.verbose:
                    list(map(sys.stderr.write,
                             ("# xp: ", cls.__name__, ".export_ for `", file_,
                              "` using `", export_call,"`\n")))

            for import_section in import_sections:
                # this calls RtAdHoc.export__
                import_section = re.sub('^\\s+', '', import_section)
                import_section = re.sub(
                    '^[^(]*(?s)', export_call, import_section)
                try:
                    #RtAdHoc = cls # export_call takes care of this
                    exec(import_section, globals(), locals())
                except IndentationError:
                    sys.stderr.write("!!! IndentationError !!!\n")
        else:
            xfile = cls.check_xfile(file_, cls.export_dir)
            if xfile is not None:
                cls.write_source(xfile, source, mtime, mode)
                if cls.verbose:
                    list(map(sys.stderr.write,
                             ("# xp: ", cls.__name__, ".export_ for `", file_,
                              "` using `", export_call,"`\n")))
        cls.flat = cflat

    @classmethod
    def export(cls, file_=None, source=None):                # |:clm:|
        file_, source = cls.std_source_param(file_, source)
        sv_import = cls.import_
        cls.import_ = cls.export__

        file_ = os.path.basename(file_)
        cls.export_(source, file_, None, None, False)
        sv_extract_dir = cls.extract_dir
        cls.extract_dir = cls.export_dir
        engine_tag = cls.section_tag('adhoc_run_time_engine')
        engine_source = cls.export_source(
            source, no_remove=True, no_disable=True)
        engine_source = cls.get_named_template(
            None, file_, engine_source, tag=engine_tag, ignore_mark=True)
        if engine_source:
            efile = cls.check_xfile('rt_adhoc.py')
            if efile is not None:
                cls.write_source(efile, engine_source)
        cls.extract_dir = sv_extract_dir
        for init_dir in cls.export_need_init:
            if not cls.export_have_init[init_dir]:
                if cls.verbose:
                    list(map(sys.stderr.write,
                             ("# xp: create __init__.py in `", init_dir, "`\n")))
                inf = open(os.path.join(
                    cls.export_dir, init_dir, '__init__.py'), 'w')
                inf.write('')
                inf.close()
        cls.import_ = sv_import

    @classmethod
    def dump__(cls, mod_name=None, file_=None, mtime=None, # |:clm:||:api_fi:|
               mode=None, zipped=True, flat=None, source64=None):
        if cls.verbose:
            list(map(sys.stderr.write,
                     ("# xf: ", cls.__name__, ": dumping `", file_, "`\n")))
        source = cls.unpack_file(source64, zipped=zipped, decode=False)
        return source

    @classmethod
    def dump_(cls, dump_section, dump_type=None):            # |:clm:|
        if dump_type is None:
            dump_type = 'adhoc_import'
        if not dump_section:
            return ''
        dump_call = ''.join(('unpacked = ', cls.__name__, '.dump__'))
        dump_section = re.sub('^\\s+', '', dump_section)
        dump_section = re.sub(
            '^[^(]*(?s)', dump_call, dump_section)
        dump_dict = {'unpacked': ''}
        try:
            #RtAdHoc = cls # dump_call takes care of this
            exec(dump_section.lstrip(), globals(), dump_dict)
        except IndentationError:
            sys.stderr.write("!!! IndentationError !!!\n")
        return dump_dict['unpacked']

    @classmethod
    def dump_file(cls, match, file_=None, source=None, tag=None, # |:clm:|
                  is_re=False):
        file_, source = cls.std_source_param(file_, source)
        if tag is None:
            tag = cls.section_tag('(adhoc_import|adhoc_update)', is_re=True)
            is_re = True
        source_sections, dump_sections = cls.tag_partition(
            source, tag, is_re, headline=True)
        dump_call = ''.join((cls.__name__, '.dump_'))
        for dump_section in dump_sections:
            tagged_line = dump_section[0]
            dump_section = dump_section[1]
            tag_arg = cls.section_tag_strip(tagged_line)
            check_match = match
            if tag_arg != match and not match.startswith('-'):
                check_match = ''.join(('-', match))
            if tag_arg != match and not match.startswith('!'):
                check_match = ''.join(('!', match))
            if tag_arg != match:
                continue
            dump_section = re.sub('^\\s+', '', dump_section)
            dump_section = re.sub(
                '^[^(]*(?s)', dump_call, dump_section)
            try:
                #RtAdHoc = cls # dump_call takes care of this
                exec(dump_section.lstrip(), globals(), locals())
            except IndentationError:
                sys.stderr.write("!!! IndentationError !!!\n")

    macro_call_delimiters = ('@|:', ':|>')
    macro_xdef_delimiters = ('<|:', ':|@')
    macros = {}

    @classmethod
    def expand_macros(cls, source, macro_call_dlm=None, macro_xdef_dlm=None): # |:clm:|
        if macro_call_dlm is None:
            macro_call_dlm = cls.macro_call_delimiters
        if macro_xdef_dlm is None:
            macro_xdef_dlm = cls.macro_xdef_delimiters
        import re
        for macro_name, macro_expansion in cls.macros.items():
            macro_tag = cls.adhoc_tag(macro_name, macro_call_dlm, False)
            macro_tag_rx = cls.adhoc_tag(macro_name, macro_call_dlm, True)
            macro_call = ''.join(('# ', macro_tag, '\n'))
            macro_call_rx = ''.join(('^[^\n]*', macro_tag_rx, '[^\n]*\n'))
            mc_tag = ''.join(('# ', cls.adhoc_tag('adhoc_macro_call', macro_xdef_dlm, False), "\n"))
            mx_tag = ''.join(('# ', cls.adhoc_tag('adhoc_macro_expansion', macro_xdef_dlm, False), "\n"))
            xdef = ''.join((
                mc_tag,
                macro_call,
                mc_tag,
                mx_tag,
                macro_expansion,
                mx_tag,
                ))
            rx = re.compile(macro_call_rx, re.M)
            source = rx.sub(xdef, source)
        return source

    @classmethod
    def has_expanded_macros(cls, source, macro_xdef_dlm=None): # |:clm:|
        if macro_xdef_dlm is None:
            macro_xdef_dlm = cls.macro_xdef_delimiters
        mx_tag = cls.adhoc_tag('adhoc_macro_expansion', macro_xdef_dlm, False)
        me_count = len(cls.tag_lines(source, mx_tag))
        return me_count > 0

    @classmethod
    def activate_macros(cls, source, macro_call_dlm=None, macro_xdef_dlm=None): # |:clm:|
        if macro_xdef_dlm is None:
            macro_xdef_dlm = cls.macro_xdef_delimiters
        if not cls.has_expanded_macros(source, macro_xdef_dlm):
            source = cls.expand_macros(source, macro_call_dlm, macro_xdef_dlm)
        sv = cls.set_delimiters (macro_xdef_dlm)
        source = cls.remove_sections(source, 'adhoc_macro_call')
        source = cls.section_tag_remove(source, 'adhoc_macro_expansion')
        cls.reset_delimiters(sv)
        return source

    @classmethod
    def collapse_macros(cls, source, macro_xdef_dlm=None):   # |:clm:|
        if macro_xdef_dlm is None:
            macro_xdef_dlm = cls.macro_xdef_delimiters
        if cls.has_expanded_macros(source, macro_xdef_dlm):
            sv = cls.set_delimiters (macro_xdef_dlm)
            source = cls.section_tag_remove(source, 'adhoc_macro_call')
            source = cls.remove_sections(source, 'adhoc_macro_expansion')
            cls.reset_delimiters(sv)
        return source

    @classmethod
    def std_template_param(cls, file_=None, source=None,     # |:clm:|
                           tag=None, is_re=False, all_=False):
        file_, source = cls.std_source_param(file_, source)
        if tag is None:
            is_re=True
            if all_:
                tag = cls.section_tag('adhoc_(template(_v)?|import|unpack)', is_re=is_re)
            else:
                tag = cls.section_tag('adhoc_template(_v)?', is_re=is_re)
        source = cls.activate_macros(source)
        return (file_, source, tag, is_re)

    @classmethod
    def get_templates(cls, file_=None, source=None,          # |:clm:|
                      tag=None, is_re=False,
                      ignore_mark=False, all_=False):
        file_, source, tag, is_re = cls.std_template_param(
            file_, source, tag, is_re, all_)
        source = cls.enable_sections(source, 'adhoc_uncomment')
        source = cls.indent_sections(source, 'adhoc_indent')
        source_sections, template_sections = cls.tag_partition(
            source, tag, is_re=is_re, headline=True)
        templates = {}
        for template_section in template_sections:
            tagged_line = template_section[0]
            section = template_section[1]
            tag, tag_arg = cls.section_tag_parse(tagged_line)
            if not tag_arg:
                tag_arg = '-'
            if tag_arg in cls.template_process_hooks:
                section = cls.template_process_hooks[tag_arg](cls, section, tag, tag_arg)
            if ignore_mark:
                tag_arg = '-'
            if tag_arg not in templates:
                templates[tag_arg] = [[section], tag]
            else:
                templates[tag_arg][0].append(section)
        if all_:
            result = dict([(m, (''.join(t[0]), t[1])) for m, t in templates.items()])
        else:
            result = dict([(m, ''.join(t[0])) for m, t in templates.items()])
        return result

    @classmethod
    def template_list(cls, file_=None, source=None,          # |:clm:|
                      tag=None, is_re=False, all_=False):
        file_, source, tag, is_re = cls.std_template_param(
            file_, source, tag, is_re, all_)
        templates = cls.get_templates(file_, source, tag, is_re, all_=all_)
        if all_:
            templates.update([(k, ('', v)) for k, v in cls.extra_templates])
            result = list(sorted(
                [(k, v[1]) for k, v in templates.items()],
                key=lambda kt: '||'.join((
                    kt[1],
                    (((not (kt[0].startswith('-') or kt[0].startswith('!')))
                      and (kt[0]))
                     or (kt[0][1:]))))))
        else:
            templates.update(filter(
                lambda tdef: (tdef[1] == 'adhoc_template'
                              or tdef[1] == 'adhoc_template_v'),
                cls.extra_templates))
            result = list(sorted(
                templates.keys(),
                key=lambda kt: '||'.join((
                    (((not (kt.startswith('-') or kt.startswith('!')))
                      and (kt)) or (kt[1:]))))))
        return result

    @classmethod
    def col_param_closure(cls):                              # |:clm:|
        mw = [0, "", ""]
        def set_(col):                                       # |:clo:|
            lc = len(col)
            if mw[0] < lc:
                mw[0] = lc
                mw[1] = " " * lc
                mw[2] = "=" * lc
            return col
        def get_():                                          # |:clo:|
            return mw
        return set_, get_

    @classmethod
    def template_table(cls, file_=None, source=None,         # |:clm:|
                       tag=None, is_re=False):
        file_, source, tag, is_re = cls.std_template_param(
            file_, source, tag, is_re, all_=True)
        # Parse table
        table = []
        tpl_arg_name = (lambda t: (((not (t.startswith('-') or t.startswith('!'))) and (t)) or (t[1:])))
        col_param = [cls.col_param_closure() for i in range(3)]
        table.append((col_param[0][0]('Command'), col_param[1][0]('Template'), col_param[2][0]('Type')))
        table.extend([(col_param[0][0](''.join((
            os.path.basename(file_), ' --template ',
            tpl_arg_name(t[0]))).rstrip()),
                       col_param[1][0](''.join(('# ', t[0])).rstrip()),
                       col_param[2][0](''.join((t[1])).rstrip()),
                       )
                      for t in cls.template_list(file_, source, tag, is_re, all_=True)])
        # Setup table output
        mw, padding = (col_param[0][1]()[0], col_param[0][1]()[1])
        mw1, padding1 = (col_param[1][1]()[0], col_param[1][1]()[1])
        mw2, padding2 = (col_param[2][1]()[0], col_param[2][1]()[1])
        sep = ' '.join([cp[1]()[2] for cp in col_param])
        make_row_c = lambda row: ''.join((
            ''.join((padding[:int((mw-len(row[0]))/2)], row[0], padding))[:mw],
            ' ', ''.join((padding1[:int((mw1-len(row[1]))/2)],
                          row[1], padding1))[:mw1],
            ' ', ''.join((padding2[:int((mw2-len(row[2]))/2)],
                          row[2], padding2))[:mw2].rstrip()))
        make_row = lambda row: ''.join((''.join((row[0], padding))[:mw],
                                        ' ', ''.join((row[1], padding))[:mw1],
                                        ' ', row[2])).rstrip()
        # Generate table
        output = []
        output.append(sep)
        output.append(make_row_c(table.pop(0)))
        if table:
            output.append(sep)
            output.extend([make_row(row) for row in table])
        output.append(sep)
        return output

    @classmethod
    def get_named_template(cls, name=None, file_=None, source=None, # |:clm:|
                           tag=None, is_re=False, ignore_mark=False):
        if name is None:
            name = '-'
        file_, source, tag, is_re = cls.std_template_param(
            file_, source, tag, is_re, all_=True)
        templates = cls.get_templates(
            file_, source, tag, is_re=is_re, ignore_mark=ignore_mark, all_=True)
        check_name = name
        if check_name not in templates and not name.startswith('-'):
            check_name = ''.join(('-', name))
        if check_name not in templates and not name.startswith('!'):
            check_name = ''.join(('!', name))
        if check_name in templates:
            template_set = templates[check_name]
        else:
            template_set = ['', 'adhoc_template']
        template = template_set[0]
        template_type = template_set[1]
        if check_name.startswith('!'):
            template = cls.dump_(template, template_type)
        return template

    @classmethod
    def extract_templates(cls, file_=None, source=None,      # |:clm:|
                          tag=None, is_re=False, ignore_mark=False,
                          export=False):
        file_, source, tag, is_re = cls.std_template_param(
            file_, source, tag, is_re)
        templates = cls.get_templates(
            file_, source, tag, is_re=is_re, ignore_mark=ignore_mark)
        sv_extract_warn = cls.extract_warn
        cls.extract_warn = True
        for outf, template in sorted(templates.items()):
            if outf.startswith('-'):
                outf = '-'
            if outf == '-' and export:
                continue
            xfile = cls.check_xfile(outf, cls.extract_dir)
            if xfile is not None:
                cls.write_source(xfile, template)
        cls.extract_warn = sv_extract_warn


    def compileFile(self, file_name, for_=None, zipped=True, forced=None): # |:mth:|
        file_name, source = self.std_source_param(file_name, None)
        return source
# @:adhoc_run_time_engine:@
# @:adhoc_remove:@
# @:adhoc_remove:@
# @:adhoc_run_time_engine:@
# @:adhoc_run_time_engine:@
# @:adhoc_remove:@
usage = """Usage: echafaudage [options] -s <scaffolding> [<TARGET>]

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
# @:adhoc_import:@ !docopt
RtAdHoc.import_('docopt', file_='echafaudage/docopt.py',
    mtime='2013-03-27T13:03:22', mode=int("100644", 8),
    zipped=True, flat=None, source64=
    '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'
    'P9jwqd+yB/R/AZsnPBM/+gAA')
# @:adhoc_import:@
from docopt import docopt  # @:adhoc:@
# @:adhoc_import:@ !echafaudage
RtAdHoc.import_('echafaudage', file_='echafaudage/__init__.py',
    mtime='2013-03-27T13:34:42', mode=int("100644", 8),
    zipped=True, flat=None, source64=
    'H4sIAMCCU1EC/4uPL0stKs7Mz4uPV7BVUDfQM9QzUOcCAIIKcekWAAAA')
# @:adhoc_import:@
# @:adhoc_import:@ !echafaudage.tempita
RtAdHoc.import_('echafaudage.tempita', file_='echafaudage/tempita.py',
    mtime='2013-03-27T23:07:05', mode=int("100644", 8),
    zipped=True, flat=None, source64=
    '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'
    'c9IubGf+FxCv4/HIjQEA')
# @:adhoc_import:@
import echafaudage.tempita  # @:adhoc:@


def copy_dir(source, dest, vars=None, source_origin=None, ignores=None):
    if source_origin is None:
        source_origin = source

    if ignores is None:
        ignores = []

    if vars is None:
        vars = {}

    if os.path.isfile(dest):
        print('Error: %s is a file and not a folder' % dest)
        sys.exit(1)

    if not os.path.exists(dest):
        os.makedirs(dest)

    names = sorted(os.listdir(source))
    for name in names:
        full_src = os.path.join(source, name)
        if (
            name in ('scaffolding.json', '.git', '.hg') or
            full_src[len(source_origin):].lstrip('/') in (ignores)
        ):
            continue

        full_dest = os.path.join(dest, echafaudage.tempita.sub(name, **vars))

        if os.path.isfile(full_src):
            if name.endswith('.tmpl'):
                full_dest = full_dest[:-len('.tmpl')]
                f = open(full_src, 'rb')
                content = f.read()
                f.close()

                f = open(full_dest, 'wb')
                f.write(
                    echafaudage.tempita.sub(content, **vars)
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
                vars,
                source_origin,
                ignores
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

    if json_data and ('ignores' in json_data):
        ignores = json_data['ignores']
    else:
        ignores = []

    copy_dir(
        source=os.path.abspath(scaffolding_source),
        dest=os.path.abspath(arguments['<TARGET>']),
        vars=vars,
        ignores=ignores
    )
    if tmp_dir:
        shutil.rmtree(tmp_dir)

if __name__ == '__main__':
    main()
