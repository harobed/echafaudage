# -*- coding: utf8 -*-
# @:adhoc_run_time:@
# @:adhoc_remove:@
# @:adhoc_run_time_engine:@
# -*- coding: utf-8 -*-
# @:adhoc_compiled:@ 2013-05-27 16:02:05.769532
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
    'P9jwqd+wB/R/AaO6pq0/+gAA')
# @:adhoc_import:@
from docopt import docopt  # @:adhoc:@
# @:adhoc_import:@ !echafaudage
RtAdHoc.import_('echafaudage', file_='echafaudage/__init__.py',
    mtime='2013-03-27T13:34:42', mode=int("100644", 8),
    zipped=True, flat=None, source64=
    'H4sIAF1no1EC/4uPL0stKs7Mz4uPV7BVUDfQM9QzUOcCAIIKcekWAAAA')
# @:adhoc_import:@
# @:adhoc_import:@ !echafaudage.tempita
RtAdHoc.import_('echafaudage.tempita', file_='echafaudage/tempita.py',
    mtime='2013-03-27T23:07:05', mode=int("100644", 8),
    zipped=True, flat=None, source64=
    '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'
    'yI0BAA==')
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
            scaffolding_source = os.path.join(
                tmp_dir,
                'content',
                os.listdir(os.path.join(tmp_dir, 'content'))[0]
            )
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
