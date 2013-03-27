# -*- coding: utf8 -*-
# @:adhoc_run_time:@
# @:adhoc_remove:@
# @:adhoc_run_time_engine:@
# -*- coding: utf-8 -*-
# @:adhoc_compiled:@ 2013-03-27 14:32:44.810880
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
# @:adhoc_import:@ !docopt
RtAdHoc.import_('docopt', file_='echafauder/docopt.py',
    mtime='2013-03-27T13:03:22', mode=int("100644", 8),
    zipped=True, flat=None, source64=
    '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'
    'Bxs+9Rv2gP4bXP2CCD/6AAA=')
# @:adhoc_import:@
from docopt import docopt  # @:adhoc:@
# @:adhoc_import:@ !echafauder
RtAdHoc.import_('echafauder', file_='echafauder/__init__.py',
    mtime='2013-03-27T13:34:42', mode=int("100644", 8),
    zipped=True, flat=None, source64=
    'H4sIAPz0UlEC/4uPL0stKs7Mz4uPV7BVUDfQM9QzUOcCAIIKcekWAAAA')
# @:adhoc_import:@
# @:adhoc_import:@ !echafauder.tempita
RtAdHoc.import_('echafauder.tempita', file_='echafauder/tempita.py',
    mtime='2013-03-27T14:32:41', mode=int("100644", 8),
    zipped=True, flat=None, source64=
    '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'
    'Z3e5/tz1lxZmd7qFuUFhec7rdz/Nvr56c93GXLP58Pzlcml25ZjLd+fLc7MnO/2V2lwtmNsb'
    'NA8Wl0+eu49zztdaYXalePRcra8XtxYLc3NL/ixZjtejg1H9+Ply9jWYq9WXzgZz3fuVp+dH'
    'ztyX8zuNleVPs9DQYHnw6i00r7ru0uq8c+O4tZPRQ/3L/PnJxe7DeuFq57LuD4+2FtYXN4db'
    'T+368LmwUfzqHTornN8FA2enubS/+XUxON58eZk9qO8Wnva/+jf7O7uXi9XtVXd/e33z8ua1'
    'S+SWUa8b7KzO17547uHCPTmGXIy23NX18+oWvz2erS0e9x6Hl97Wlx3vcWVzh3DK/c5Wb3TW'
    '21u8eTzrrbpnh63Nnc36U3799fQ1P1edG+Svzr72Pz3tPD84B07hauvLLsc7N2i1Tve257fm'
    '75/O1h5d17u+7i1eLJ/3nOLqPlmXXu18/fW8Ot86c0be5drR4tPWQu30YON5fu1rtXU6V9tr'
    'nD0PuNXCqNNY3qqfPsw/vPodsN5YPTjd2Nt/2N5bH6yuzV1tbTy3XudvOluLXw8WR0X/+nrj'
    'pTUYzu5dBrvPzydX/f7N0+nuI1dDB+tHS08LL4cv1eejYHvjYG3/xL/Z9A+ejtfmLmdXC9f9'
    'g9b+w6C4sLYcrD0tnp+tX54GnYWDT73rwfZ9a9VtH4++XOzw64/+6uqVf3q95pytrXl+bW2z'
    'veEc3wf1q/bT9uni3O7T9s79/Jfz48XVQ7fW+XLxyVl5IbJOrbOYr/tfNgq7K4NtcoI44DTr'
    'nq+0Hs+dgffSag4JbjxcLj4vu/3Cw5d80DjOH18Ol1rV49cFwi4Xll/6g9Pmp87F+VNzY1jY'
    'IMKtSw5xB1crHLri4MQ9fNz4dLGwv/Xauz+sXq36G62H/VFvo9V/Odt/Ikf5YKe2cHBxcjHq'
    'Oa3HL/Wz44O1+av5tfOb9f0vwePR+d7lORe1P20Nth+a8w/L25vL+b2Lw0eCsMPTy4XF3a4z'
    '67gLo+P6697T07H7ZXC/8zK3WvtysODMf62+zC+c9Dun/t7CvddwPGG7eLW6Olj7NNzZ3hls'
    'Ovf51+Pap7W1q90Td7Syf7a/0ykcr106N+fLq8VhsHR6P1jo7DzcFIPt3cLweWGtsefdXC9f'
    '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'
    'sJ36H6ALLnPDjQEA')
# @:adhoc_import:@
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
