# -*- coding: utf8 -*-
# @:adhoc_run_time:@
# @:adhoc_remove:@
# @:adhoc_run_time_engine:@
# -*- coding: utf-8 -*-
# @:adhoc_compiled:@ 2013-03-27 23:11:17.042527
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
    'wYZP/YY9oP8Lv1fHMD/6AAA=')
# @:adhoc_import:@
from docopt import docopt  # @:adhoc:@
# @:adhoc_import:@ !echafaudage
RtAdHoc.import_('echafaudage', file_='echafaudage/__init__.py',
    mtime='2013-03-27T13:34:42', mode=int("100644", 8),
    zipped=True, flat=None, source64=
    'H4sIAIVuU1EC/4uPL0stKs7Mz4uPV7BVUDfQM9QzUOcCAIIKcekWAAAA')
# @:adhoc_import:@
# @:adhoc_import:@ !echafaudage.tempita
RtAdHoc.import_('echafaudage.tempita', file_='echafaudage/tempita.py',
    mtime='2013-03-27T23:07:05', mode=int("100644", 8),
    zipped=True, flat=None, source64=
    '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'
    'vjx3F+vLz88bW/b29vLizcRu3nS2hpvNtdvaZPP8lEzC8JkvRf7dtltb3Dxze2Rpm+7W2H4+'
    'bW+5zyvby8OaPVosLX5YDUb1s5vH5fWtp9Mv3ZZd85+X68tP3cdu//lojyzhp81lYVPhk2EG'
    '2wQV71YbfnVtubG3m2+vrD83Lp/rh/mt3XFp+2KysttaH34ej683r8/PB+cr58Hnx2/Lt+fb'
    'F+3xZv7ZueNL0RzuuJfDx88bV3uf1k+OnXr5pDrqrH9xvHH322Wrdee1W93965P+82UQtG6P'
    'Lk9OB+WDw73dj5+vDleP2+X+zvVp74bfpmx+OT/8fP75cPtyb+Pq45Vzt3F92e05Qad7aR9e'
    'Hx6WdztEfNtt3xz1d47XGv3lzaD2yXbzj/Zhe3N77bzW9dpbpBjfK0rl68vm4EOvXL0uVz95'
    'zsHH6sA+WXHOh61DZ9s9reXJgTV/sn7Yre+fXT5+uWifDk+vzg+2jz7u90vD1a0vK7WNnhC1'
    'u/0PV7u1k2B9491Zud4rHa+0zm+9Dxvn/uiWiHXN5rvg7uDuYnC7ZwfO7f7u7nJ5j+y/j/bO'
    'Zm01/+xfV6/3dw64Wsbzm4eTD7tbq60RORWujwadjad+eXS47NY/1pyTp73qxqR5fjYYPW22'
    'Tr3P1yXnxu87H9Y2apMPO9Wd9U8XwfWH0oifyW5PPn4r3e0clJyLbweT0Yd3jbzTWjk5mizv'
    'eaVxJ3+0N6mOPnW3zo8vTx53jxYPLt+5t1/O9jobwefRwbvO6vhio9Z/4jJK7+Mi4Z6Dm5J9'
    'dTZqDcafBls3/bxd6zl3q8O96v7lZHvcOLjbcm/sen9ys9Z6XLy6/LR6Nl7faO/kTy5aR2vt'
    'vXqbM6ibj6N952D7MDjZ6XUmnZPa8fWH88+du9JwQra9Up5QyJcTf7vnfPQ3So9Xk/Od8kH+'
    'af2oWu6Rc8un1erRt9Jue8z3isnm7vhx/XK7VrY3Os7Hy+rh5fqOt7W1chU0Dy5u3jWP70r5'
    'i4/j8vL5447fPtk5WBxe3gxvt+r7T7XTlXKpmj8dXpb41VFpZ+fmU/nu8XlvZXd4u1kjQv7j'
    'Tn//oHfV+Piu/OH56GjvsFn2tsvuhn2yP3q3VdvNd8ar7ePm7V1wMiyVDvuN2qC3J9Qy7+zz'
    '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'
    'PjHIjQEA')
# @:adhoc_import:@
import echafaudage.tempita  # @:adhoc:@


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
