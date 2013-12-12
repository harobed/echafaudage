# -*- coding: utf8 -*-
# @:adhoc_run_time:@
# @:adhoc_remove:@
# @:adhoc_run_time_engine:@
# -*- coding: utf-8 -*-
# @:adhoc_compiled:@ 2013-12-12 20:53:38.472696
import sys
import os
import re

# @:adhoc_uncomment:@
# @:adhoc_template:@ -catch-stdout
try:
    from cStringIO import StringIO as _AdHocBytesIO, StringIO as _AdHocStringIO
except ImportError:
    try:
        from StringIO import StringIO as _AdHocBytesIO, StringIO as _AdHocStringIO
    except ImportError:
        from io import BytesIO as _AdHocBytesIO, StringIO as _AdHocStringIO

# @:adhoc_template:@
# @:adhoc_uncomment:@
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

    tt_ide = False
    tt_comment = ''
    tt_prefix = ''
    tt_suffix = ''

    @classmethod
    def template_table(cls, file_=None, source=None,         # |:clm:|
                       tag=None, is_re=False):
        file_, source, tag, is_re = cls.std_template_param(
            file_, source, tag, is_re, all_=True)
        pfx = cls.tt_prefix
        sfx = cls.tt_suffix
        comm = cls.tt_comment
        if comm:
            comm = ''.join((comm, ' '))
            pfx = ''.join((comm, pfx))
        if cls.tt_ide:
            command = ''.join(('python ', file_))
        else:
            command = os.path.basename(file_)
        # Parse table
        table = []
        tpl_arg_name = (lambda t: (((not (t.startswith('-') or t.startswith('!'))) and (t)) or (t[1:])))
        col_param = [cls.col_param_closure() for i in range(3)]
        table.append((col_param[0][0]('Command'), col_param[1][0]('Template'), col_param[2][0]('Type')))
        table.extend([
            (col_param[0][0](''.join((
                pfx,
                command, ' --template ',
                tpl_arg_name(t[0])
                )).rstrip()),
             col_param[1][0](''.join((
                 '# ', t[0]
                 )).rstrip()),
             col_param[2][0](''.join((
                 t[1], sfx
                 )).rstrip()),)
            for t in cls.template_list(file_, source, tag, is_re, all_=True)])
        if cls.tt_ide:
            itable = []
            headers = table.pop(0)
            this_type = None
            last_type = None
            for cols in reversed(table):
                this_type = cols[2].replace('")', '')
                if last_type is not None:
                    if last_type != this_type:
                        itable.append((''.join((comm, ':ide: +#-+')), '', ''))
                        itable.append((''.join((comm, '. ', last_type, '()')), '', ''))
                        itable.append(('', '', ''))
                itable.append((''.join((comm, ':ide: ', cols[1].replace('#', 'AdHoc:'))), '', ''))
                itable.append(cols)
                itable.append(('', '', ''))
                last_type = this_type
            if last_type is not None:
                itable.append((''.join((comm, ':ide: +#-+')), '', ''))
                itable.append((''.join((comm, '. ', last_type, '()')), '', ''))
            table = [headers]
            table.extend(itable)
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
    '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')
# @:adhoc_import:@
from docopt import docopt  # @:adhoc:@
# @:adhoc_import:@ !echafaudage
RtAdHoc.import_('echafaudage', file_='echafaudage/__init__.py',
    mtime='2013-03-27T13:34:42', mode=int("100644", 8),
    zipped=True, flat=None, source64=
    'H4sIAEIUqlIC/4uPL0stKs7Mz4uPV7BVUDfQM9QzUOcCAIIKcekWAAAA')
# @:adhoc_import:@
# @:adhoc_import:@ !echafaudage.tempita
RtAdHoc.import_('echafaudage.tempita', file_='echafaudage/tempita.py',
    mtime='2013-03-27T23:07:05', mode=int("100644", 8),
    zipped=True, flat=None, source64=
    'H4sIAEIUqlIC/+y9aZviRtIo+r1/BbbPPEWZ7kISe93j9x0QIASSAEmsPf2WtSEJrWgBxHj+'
    '+9EKSAiq2vZ47n3uqbarQMqMjIyMjC0jM38q/P2V4SWDe7Nc/c2RNeH1759+ujwUNGOfeRSX'
    'exN0Udajd19+/lLgDF7WxdeC62y+NIMnV3U4QzNlVeBf/16AALDyBYT8//yPr7XKa6X5Um1A'
    '9Vb9k6yZhuUUbM9OPhrnT5bw6Qqeq/sQNUF3Upg5gmaqjOOjVPjCMQ4nfbEd3nCdT47lvX4q'
    '+D8by9AKHOVYPqbouBDDPn9n7MJbmx8YXMdzBBsdf855lTz5JBw5wXQKaAijZ1mGFbVxbuzc'
    '4J/TXgDuXpvnpmQjaSQG+X1t5BLzDt05lbHtAumEEIoGuxU45/m18JGfnwq//fbbK6far/7f'
    'sAOqz0lvvKDKmuwIll34pVB8+vvr0+fC0+vfn57DIrYPXzb0B6Ui8sd4v5mWwQm2/SYZhhIU'
    '/ee/YhI6FnPuXfDi67dP8ZuAcG+8bPkPn97eoi6/PV2qcee3L9HTjQ/D/0pbrhB9NyxO4P0n'
    'fUa1hU8Jz50EPf1s58qCc34UPNkLFmvYQuoZL7CumK4o65zq8n7nGEeKUL/CXBcE/k3WZee6'
    't+EbidkLN2+iDh0YK4McL2wKceftkDHeXEdWi88XVgtKyHb0Mhj5q1fBjyU4rg9UtmXddhid'
    'E4IynwssYwtRnedz8dRkCTuYgP3xx0upmO0JRhMyTP8BbB5g5Nd5LhjWLabBVHlOdffN5Yox'
    '8rmddXXZF4BCXMbnyFAMPj3oaQDx4530S/ujpDIayzOF42vheH7r+nPVMwPOCf4UY7Bp7P1n'
    'e0Z1hQzu8hXhovcFRucLuuFckyR88zlp5z51386t5BEofPMp89BvwZE5TXAkgy8mqDyf2/qc'
    'LuBy8RxPSl4VDMmTx7VRjb9fAzpzeSzpGLFoexprqG+G5Wu8z4WLiPnst+U/+iWcHpF084XX'
    '60bnXn87d0blVc1v/VLrK/Dt0tObl+DlZTgAPvw0TWN4lvAi2Bzjj2nwIEPUbBErVSQm79PT'
    'y9aQ9WIIwCdmqpNhjYQ8oTDPUMeny5ttqrJT9CV1OFlCkvuPc6hyJdoz1PH7GDHUTT99SKk+'
    '+N+vumBE72LToXjuy9P/fP2ff+jffi4+xbg8PUcP/tfTs886fhX8mhC2qzoXSRmSl7Ed33gJ'
    'xDRwfhj1zn/k9/WFF4K5/GYbri/Oi1mZ5Qv5gubrWT1oayPrfDCsRctISJSZIT7nWQEGmvES'
    'fiwC6aGMMPHf+h+y7yL0XxjTDF4WQ3onzXxN+vEagv32/LBqoKLONcMKr/7zEpitdkWc8P2n'
    '70PlGlzMhFHFB3wWzUKTsWzhLbADInbzh1b01VnwIM25vxBG8ChgNE7Vrhjt5ucy5+I6V1wb'
    'oW6+xfZMWOBq4HymvbIzZLsQvM+qnSs7JOCajA1zDesa/zvQHkiJBCG/tzedTUH+5TLjn77+'
    'jz8//Cq+LPKnyLfSU2agBZ8I3wXuH/+wb6GEFL22gB7P+Az4y9S/fnGlM30JZB1j8l6E9QWr'
    'QAakpdrTcygFbiV4gOEFshZLF1tgLE4qRg2lmO75ujuake6HGYkuf9KKluGaRfBKjd/QNS78'
    '9JQSNmbUsyux9vJzJNFCTJ58cv98Te3gBWPFAtN22WICxC/7lMb8JXxVTPUgxe03YjgNOWz7'
    'pxCdGHTw/mZiF81Q/J5f35/htuBcTYxofmdmSzxDb438eGbmzPdzmbdAuQf8VMyZhp9D5rmF'
    'm6JO1v3InaK3PkoGg2u1n5D91mnJhX3Xwck2cSUW/DcfbyAX+D2J9R1kDKj+iEp5Q3rDSZlO'
    'PuAkX5nk8FKmftYLvWWd7+vgx9Hz3bMMch/wiC/oXVjSh7ORLdu52PyB9C8Ui8VAsgaWW2ip'
    '+6LwOfRgipGkL5QKkVV3DShQzt8DJwLy9UvKNjDcoP8psnwtntGMm/cFb9Jg+OTGusj+BKZU'
    '0KJvS+XO3U+FD/7cmePfspwWlUtx0M/Zrj2SZCGCgQ6KTOKU6nloE6f57wqbez5ILouGTTyW'
    'tBENvgvF343fLcU/gGKgL4KO2d/rVmRRvLXsA3aKcQpYKkDx4sTcNnTrDceVfVbO83KvDeCk'
    'pM/i323wBjj55q4jBxAeU+FzQRIYPiDXmSq3pJD1t6TX1+Gj4Ic1eC9sy05TKi6feXplRKQN'
    'ln8rYVPoh4bj+cFN2TSGl0G4KcgZuiPrV0Zp4m6fYecgsjlT+zVX8iRUO3tBaSflwhK3Ui/f'
    '3M4DmsdZ9yFcBvgDnHkpfMbWfi8AEBf7E9g0r/XYtk/PiNtWLvBv+vSBfiRCO/IxP+Zepjr3'
    'rq/50Je8EaZXru5dNPIVwIf0YUyxNE6pbx/RcG+RE/EfJFZm2B6QKq/Hz4FU+JCi/P8eW+To'
    '3b+AM65J9h9njtvx+3P5w7EY3fbVnnZtq5wfXiThO47Go/hKhjQ3Lu+/JRiVZzY9sB8eKv5P'
    '2YELCPLIZry1E/MNBlY12Pvq/U80J+KGzuNaDB48iqOm35+DxkkUJyp8q6PCch/itrS+fchw'
    'H4iAFh7Z/7+XJxJV/B0m4l1OufZXclD9T/PHOwZjhhoBWrllco3RMHzzCHoA7vM1/DSb5tlE'
    '+UybX+4vYeyzDrcEndGEtBWZWY8KS/DvScU8/yd3Fe1MrUvsI+jk6zl+mt96mhC3RvddsMHv'
    'F0swVYYT8oE/5ymyrKLJmfK5yuz74hVxIs8j+n832e9S4koq/GUdvbYHfh+v/V/WSih+L2D+'
    'Uep/B6f9Jxnr+7sp67xvOd7xib+vj9+pc6OWUyvW/39VuJflqqwfEDkltybcFfC48utdk+lM'
    'aFl3ijcrXx+L6KTgfKl+IIqT6nYYkY/qv97rRwz+fxeA+yiE64v5GRTByp7/7+dC8UsE6fk2'
    'deKOrWwdozXCp6w8y7FtQhz/67twDFD7LjzCbkRNPcIoZwL9ZUaQL6JZVfhTxEYM6iY55n+K'
    'Xwv/cP5hffv5ufhT4b+fb6iY4OAGtHv6xz/Ap/fErW9fqq+F4rnFkNwXMDGxg1LvKJ9zvz8m'
    'mGMBHCcbH/2Zzb5xksApOV3+9vM/nHRfz9V42Y5QlTVTFR5y2bmO5k/CWMbfb/G5+PV/Qlr/'
    'Q//22/+6tH5//BNULvZ7xAERXa5ip7Gpdce7i9MqcoVjsiR/A/P503X9i3N+TdgkCyKunJH9'
    'P/lCk7ULjCUUhL2sZiV/ADJOXr2d5qpsO0WNMX1V44tqhxcs6+Vg+Xr2Qbyq+PRTgXdew8bC'
    'pn29H9DYtM4IBukR+tPzc26iYfFT3uLgHb4ImToXFx+Lp/MYvVhxSsVzoRS2fYt/DsEv7HTr'
    'KkcJZCnMstx3yS3LH5gz6Lw0lJSeyFU44QrwFYo+UqqgFy9Pnn3RHTxJNES+FE91Mvpw6+ae'
    'MYRyoNwj01ngWwKjnJ/mkCs9TVP1r3RekCt0qeOz0G/BTA4SB5+vMwc/3Vo1QWaefZAdqRiy'
    'XW5ixZV19Prlyj7iL+8zC5URB+R05w+Pu6+nUq+hG7aIrLAQTJLwG1S6HZufVIHZC76oZ3Ql'
    'dCbt6PNNwaSfiSoNKfUBy+dcTzg64ZLaeXh+iqa97SSz/Sb/KBlc/iIXMrPwoTj+c8z4Rwrv'
    'U1YK3WiCj2jCO4kwgZf1p/SBkfz3DuNTzfdRwy8BaD53ae4P+xX3UpSvkHiYsh1Kxrdor1Ex'
    'StB9P8UmNyk5qpzmSMFH2xbC3RppOzGYsFwwX/NqnQMF55R5LkiEce5ITNV5u1hajG9HvRYY'
    '35K/EzqUrOvSr8GDIvM968s5zaWyNR+2xrwjjaNKkan09dt3k8zHLaAVCDXu0CpShLFMCbAr'
    'cjmL64EZUvjll1BO5MM5D2zplwJ4z6m6jP4vBei+z3KfAgkzh9/TaGYSTp++fP3525eXn+NN'
    'c0HCpa+M/p8wx/b55efwrS/+MoBuBzkEG5iNj7JVo0Y+nK96Lh7vYbkRduH7RwI2lT4fSaZ3'
    'Z+p9ezeHfa7ErssFyWu3ucfnuRjV/xwXjvawhFpPYmzGcaxzgacI7xsFH74O9Hv4Id4cEKar'
    '5QmjW/cwfP7QPfyLyOWzZ9RW8WZ3Ulp8fZxkEbz3SBa3+ueRzJ+BfIpgG9/ye/scc16U6/36'
    'PsnOeGZnUEDIEGRgFUcfAvHy5SnrGk08Hy+9EhDGF+Ksu9kIViEgkcy6jhDKQFbWGcvzBaHp'
    'Oi9ZQ+xM0Mg/kn3P7SmC8pQjES90TYq/RIVfAoIUP5TgfwsiUzcvLu3lANr4QAxfLhdj2j9Z'
    '7NPzg/Y2eUhGkF441Xcfs/jHe13HObvhLjY07/rOfaBk/O5E33x3NNhqZhef70bPilHJuxL+'
    'mtWjop+DDaFhR9+enh/Wi8q/JKUDvgk/PT+IFfoY5TSX7D99nEJ7i+vLuaoPJqL/0/OD5lPD'
    'lAXxEs/FR5XTCvFsWuVnKliMbAvJqBZj/KIJZ7h+X4Jh/fXJd7N96zJirdDn/jUtrKKJflcp'
    'ZDZwRWLmu6VMGKnIEzOJ+NOCffBxmosWCJ67a2XCmcABemmJn0Xv4/LnVoAYrvNYgpyLJZIj'
    '7GRRyCJxX4LkSoMM7AdAr6Y27euVO5M7F14W3C1+t0LpkBVKvrR5gN0dWRQaVXzI0cHQ5O/f'
    'MALt5hdL2g5q3IIJWOYxnHgDP884QlA419r1mei8czcEeWd+3x2skMf9Fnw0g5ShEMZLtHb0'
    '9HJH5MTDNg/E64NxS0AnYO8WClsG8qNKIZniJR7HMoOvxQjfp7+tvvxN+/I3nv7b4PVv+Ovf'
    'qDvoRjB8gz+h5EvwixdUhylqMmf5w8wZOm//Eiz1aHa+X3FlFYXwPl+gJR/ukd6OV5Fi2jrW'
    'JuzFj3+zf/yuBGHHvktJn+XcEGjMcsUgt9axH27rjSywY1AjJdSOvGylItDvmptBjXwhf4yO'
    'SQhl3eXghFwJl64Yy7pA1F2Xvi8CY1keFviUheKTJzgowcfB9NWkawuJRrmGnRQKQjN2MU9X'
    'h7Qq/JJp5HbAknIJxNAXDEgR0/jSbLak33Lwtxg+z8VOOMq2Y8cFslYob4T0NPaCFcq2sDk7'
    'K3qK18MRHvsQbPi5it8/X7b/B0/DQyq+J6ZfyI+k//iT39/Xwo+RP/H2FiQsBLbJj6+FAIvA'
    '1wzJ8euPCS/mg/m1EBHhpWArsmkG9V5eXv6h/3hnISBl1MccmZDT/xbmiNwSPCRkhuh+6QzN'
    '/RIaowj+i/h11rgIAT+YhSbjT8LLHEwsipPfMYG/48DkzcJIVwRHa9SrnwuiX/+6MxG4jI6U'
    'g5hB6kyYjLYTT4EaDWC9IP6vfrR4HCnTz4XW5wDETY1Yq941b24r5Cnai7sgGy+i4ISmfLaM'
    '/ypbN8cU+LjBdS4akfGFrVdjj/VuyXQs4ImxOVl++n4L09Vz+SAYyitOyPq138cGGZz9/iVB'
    'gCzWOXSIO5hjon6UtfKsrLsMZt1jsDNqAePk+JF3+SmHV+64DymG+XMciHh4o6H1zcFQ9MX+'
    'QijpEt/hyo84D+5vr4wp+6yRk9979jUybBIcR5RspI4HO5tLnmieSywmsgRiIyCjsVNEi6rm'
    'O3UhQT59ZFn4e5eEiw/UR0TfQBFcdIevJzIqITWw1zPuZrJFf87TLVoySW0aTrmEIUEy3mBi'
    '9j/IlUvM2WjrcnBUVbKQEqwIMc7b90j+Gy/hyie8sVSDeEDc+k3ILn4emE039c4m+AN5G+Nz'
    'Y6ZeA062IOf0+TXHeLjBo/hzMYVOMZd6X4HX+rfn57w8nQiT/GqP8v7Cvv2/ah7fHf6rYbg6'
    '7SIMk0UzIPryZvtEMYtJZ9Lr3mcn9XamJ47ZLY8E588FH3xvSTOvD7K55ZWfYkpBAAh+8f+D'
    'KjTYfAWqr1D96wsENmtA/dsHSPJ+kPKjHu4HPNuHHm2OJ/tHPNjv91z/NGF3zTPnjcMJl+SR'
    'L3jHSbLKx+XCOl+vUyD8J3Fux0u8PnYpF+RKXB0yoPJvCd1uApFpyr/P0meFEMvls5hOhWWC'
    'RUhBL0Y4Pt8mK/owz/G1OL78NSr87fOl759jfDLTKLcLhR9+uXT0wzbrnbhslo0FrnjVz6gG'
    'L/vK/KF8S9EvEXL+kz9BxF316zZQehnNgDu0INPrStsGx0u2fdp/7EzJKzVpZ/AwfUifbiSk'
    'Zwr2JZrzOThr9P4iYhKWD2u94OE3+vY0vIT3zvybE0WMCtw9BeYKRGLrvC/nriFHuT3XCyL5'
    'YaW3t1itvV1pgRxsoml2zf9J8W95MrR4dTjp58JI8MJPz3fDnP6f+636L1904fAWPXiAZy56'
    't6OQt4CeGbGzhflRjRhEVqKA01VU9zZSZ12tiiSlcqjyU8GRggWtjREU1BhLEfjgoFbDdQJW'
    '5T/di5S+p5DBj8T277XuW/LeH0cBSIvHgAqPlr3S6IWP/UYCiZB18mIZnQPkc1Qvv3z4Kiwe'
    'C8Cg/I0gP/cwkI/ZteLEiovfBR/vrdDkLCS+3uH8t9hJy6wl3pn2SYWrNMUX0+Oe7iVs5jQR'
    'fksnLqZjkAwXnKVbvCodCMwX8m08utNMkL0VBdyCT9c1H0TrYzK+x0j3t1f7TfntRbr1+V73'
    'k2bOpXNG7YLOXUn9BybLB/uZOQ0y5NeXs4GUAMorEyxW/XLu6wP5l0yrrH2RmqnREoZvHF1h'
    '8Ckj3e7M5oTVb4+EuZGZeSeiOXfg3UTUc9k1NgDPjHpjKzw0WzIcfKfB24H5d3Jvanjv8u8V'
    'Ma5R+69Cjs15y9GhZDD0IE9WCcdHOAiW/4bRw9chxCef1d/JDHi49BhZnmpKDCepCncrxRZG'
    'O0mveWcN8mz6vZv0EIr0P8Lw2S7kHIB0o/xvEY8ay8RrPz1mtnx/9EYK3FW8Wcw/kPmTrK69'
    'p51SyRJnTzjJ2wocQEYrpgo9/w6SJGZnmis+JxkmOdop7Q7EwaHYUHwUtstgflk7TcUlbnJA'
    'cqTMtfS7ZYWEvjeETaq9o+iT+uHftFJ/JzcnNVTXOXYZ2Zck4GcG70GKY3QMfSrFMQ6/6Uac'
    'cJ5sPfcfxGnyD3LWU8c1c4aqMqYtvGlMEBu5ObA5ZvlzS685WeznTqfT6s/HuV9fh/H0/On3'
    'VI4cnt9ZOQrl/M7K5zsR9k95VInJ/YAs2R2MGfgxgGymTepI7eymiwyIqIWn3zVoOXv/c8ct'
    'MBvuDeRH93JG4/De5H83ev9HZGNcJqHk52SZ6eGZajnz/HbjRobXrprcv2Xui8jmEqRWSTJl'
    'U9sNYmQ5RlWvjz9Or+08JaHLaySCzMB0V4M4R6bzaTbJFL+ccBycZl2KzzdOF3r+EIAbpRKc'
    'Sl/89nPxv+3nC8igk4/h5yrYn+JLVSIy+9xzTTOHUQS7wAXbMY2Nb5DJdk56ncAV062+qPEG'
    'xs8FUTVYX64GH1WDCz/lJ96GG7GYoPYdQyu7glf88YcffripV/AfBityjzgkw18PNUlY7Psm'
    'YP4BwPFUvjPLrrE83xZTzCSARnotPlv8XfX35y8g/ZEVpD9rWfSxMZNZGQ5LBukFV7k4wddQ'
    'aN/mZp2LR1cnxEbPW3iVzdubb/xkbR/ZTq65SQmdnOXKc8Grm2/i1Yp31zziDkTHbppG5qj1'
    '8PFNlDGIfqRzkELB93NY+vlmp2D2Sp+vFxDf3u9dqr2np8xxNgG8j+J3eRNd4HMX0/MVQ48w'
    'Tcee7jZ0HvarMNxVU5kljjgcdbX8HvH/B2ZkOvkqvV50AXQ/rZuLL4AKkAs+png3eJVv4MeV'
    'UjUSEIHhnoEU5kr6z7KLqLF4KjhG3B/fZbd8eW9YXlrdX6Tr47zMrNy7Lp3cjXWv8CNP7hZm'
    'GqVPOdbJlX0Tr1N83L75gI2TGOPPDxbgUk5LYqlksLvRnWGd96ybRCE8PWcCzR9Kz0mG4ia5'
    '/Jyhcz/G8F1JLHcyz+8e9/B78ntSeT5mXp5P0uNoa8jjJNFUuqhrJ6lBV8Py+ZwfdLNbNc1n'
    'gXGZ4bz8GLAcmGOqer4L7zy6d5a83jFH04WePwwk/xSLlFl6TYZ327kbv7sxT6+Z/gPm6dlE'
    'TWPwAcv0u6zTP2Ch3k/t/r/z8t8/L3M0YqQq31Pn/1mvfB/rlLhezNyp3sTP0vrlaqklu2/h'
    'nmWcZwvFaEX9jn5nDPUPmwEfNgGiG2DfovuN7ijazHWxT8/Z2g90bm7Q4hIwjFydq3hh+o6n'
    'PPii4IQMzJ99unQjVy7Z5zSA8KDrXy499gWoqBtWEHS0lEzLwVkC13Uzh0zckSVPfsejeHfg'
    '12RliPA7ZIgQyZAULs+fPmyVpXRj4HGF+330XP/kNe+ImVz3IIH07fU/Isc4Swgy+a58yKBL'
    'gTBKEMtJIT4jqJ83GKacl/yzK1KT5hp+2oMNNlY85bYVK62nO2+zie1pEXMWSI9OanA1888P'
    'S/yRtNa/KHM86PhflTf+0d0C4WDEWeHBx7NdFH4LMs9yFFnuxrxzhTuHxZ9f/5JZm8h6ndd4'
    '3DlS4lMKatbxeYroFp4m9JQdh6eXiP+uvbDrFu8YyNdF3qv46b4xfMb3IcQgeTK4NPnckafg'
    'GNp/3b/W98Y6vtDlHds4tImvUckP2p7Rurk6+LFN/Dtt4eSKtqTVrxdKfHuPmS/7mrTgOva7'
    'tlmkW9+/1zP/+Po/YrVFR8LmT5M7Zk3xesb8Fq+YmEGuR8BVeZdNnlHPhsNuIh3Xo/8d6zh5'
    'F+VkcMidnbnTMbvkkppYsp7G8YZiV7czXRfMXo2Yma2popkktPfO+829szNUh6FtFXJeEM8N'
    '/maNlAT2D/H78/7X8Fsq6PwlL58u3cRF6gVnN4VPn5//QJM/fE+TP3y8ydeP3Zb1u0XxB8Xx'
    '7xDJH18y+7DU/Q7J+9cul4X1w4yGsB+ZOzef/v7bazAIr7/9V2wdRkWPvvDNFv3fSdG/XxcN'
    '3v3zX4+dap83k6SKVKT8Gi1VS6zEKwTih/fO1E/Xv7PTKF0m3umRR49byAkSjyCfy1xDzpAv'
    'u2nASt+ME9WJNptEn0Oa2VdHskfUe/GhaTcnEkVVLmrmcm3OLeCEDjdefQpQ3m3Jj2Dd6qlL'
    'iZR0CQ/jPDdzcyJnZryyNxtHx6xeQ4juLY6e54Di3pI7k1MIZK6Bjj5e2n3K8mBCLN+4D237'
    'dCPH727kPLrf11JQ6Lqd25zgsK1bN+bStc8fr3N8BOvcg49XzB6ukDmxPTXseWe3n+2y+MT2'
    'gBq3hthHnSSJsaNO8MIj0fQdUuhPlxVnxvpDnHQBJ7xxhhtuoAt2qiUmYXTXxbnXYZu3e17P'
    'lf+rADygKuNrvX2QIPbvE/Z/vki+xJjymCKfH55fH673Xem7/N7fwLuKrp4t1OvrhQvFuxXS'
    'yZaZBL7kgMUbGXcHQM4NLLkwLoyXjhvdXKxt779/cmYTMT8wMQt/Nc/8MX753kH+3eOUGevf'
    'xzB5g/2nDnjgZp+TS99Pi/58J2SVt3vgHBBI3UsVTMO/LABw8eWzHlWAxmve5cT310GK5wWH'
    't/3zf/8Whw+iWMolcJA5JPv+Tr2HbaWaugc7Ra6sArijnrP5b1dXPj/gkmDR5ZJC9z6DfIhL'
    '8hnkTuHrpZoPc9J19664KsPvn+5ueUjHZYL27hD/Jrs6PZddPb6y9J7sz15LlakfvX56kEB8'
    '7tIfCT398jgAdWaAyO28dqOyzQe+0w1KjyJN2cLZaNMlDnFT8jbY9PlBxOnmptncmxXuXjJ1'
    'AXx9vl0mSpPc5XVmM8sINrO9SYah2Hl75JK+3a/1NYb9LXPxzHVvb68OucyZ39mTeCf6eeRz'
    'wCSvzhgG58h/jRH8FiL37SPS8AaOzwKZC9FTMv9WgJ8vZAuC3MWvRd/UO+d8OT4037Vzwqvd'
    'I8/f/5bqW+Lhf3uURZLTRqqJj8OO5XEE8NHFsgk/hItn/1bR+x+WqNfyJVnpv5u3nQXzSxpW'
    'LoNchiOK9vvjp4Q88rmwj0fO/76/LJA7FnPB4NtzPieE42L7poDA38YFwhb2AdelwN8yxq3e'
    'UwTvl/i4JcV5LTz99tvd6ENYPODtfO1ZLIY3BRWVgEWzIfFgI+Ttix+e8hbP4x19Oh/Dulck'
    'OJUyLPAVfA3OcbqGlXM4eXZY/KEO7s65PbcyoobjT4vXQjH443c5PFM0bTQ9vZPAFCisu5WD'
    'HVafP+VnAqT44fn38MOlr/7wBiHpPzrsl7HNH9jvHdXn52T0bofuoyLLdyIjQfAW5De4VriC'
    '+N4dL7ciSzsEqgT4XPjxx+D/qxuZwvtKg9xvQ33+6NkyEXwjIxJVLgnKGOrtSc8Hn4UL/9sv'
    'lHPMQ/jOr8vlvQo4q/Cj/+/nOwWgsMAvOQXOV3Soqf4GwrD4/N0H6WT7mwSVDjeOog//c9hK'
    'NLCO8yaHe48vt5j6j2Iz9rIlwX9mWsJGPqYe2e7m/OgDms0JjOcPqrZ3Xc9c1fbXqbOMzWxu'
    'knD+mVIXI/76XUSyS0DHJ/TlZUz2VBDEf5S99CWsclka9r+Hl4RmpnyEUqaY//D5ORtkiXjg'
    'tpVAVFwH3c3wCo3C+UiHx1fTJPXfS5H8qTAJbPVCyB0XIyH4lr6qyDHVwGBMDgEqJmri9Swc'
    'c2VjjmiMhGAiAxMReDUosVwL2o+3LWcEXaTm5UDHW4wuCsXK87c07olNWzxXDvQk8K34BEek'
    'CdLJLu/A6B2dqLbUSyh+6ZlCSrJHDcX3sX1N0f+22bvqxeeJHEUYIRkw1pcvyTwp5NymeD0q'
    'kW2csy5xuZUxA+CGAPeVYLTm42Q9xo+3AL3XQmhZBdP1nQaeb/YjODe+YGgdfEiGfPvQfJRz'
    'JkTwE/jw0epxxAzBHrfMYTTBQnqSRHZzJJIvr527L8OLwQzVDtlc2Pvt+LZO2E5OusN1M0El'
    'n97nm9CffnwO8xByE+IvKDzMmb0p/cMvlzYfXNmSno1ZsfkaULpQ+ulLKbxZ8ilC8/n3gnsJ'
    'ePSMov+g+Pw74T6o86EuPX2ORgG8GoWfAohh9sXr0/NDtNJNBIA+gMYDeNdsdh60T7+PEf6k'
    'Ef0zR/I8OePp+O32bSKmo2av1R8VHOYYgzBcx3SdK9PYV9kMH9/ylpbp4Lfis//3Wk8kT69P'
    '6tQO4BkGmAYC5gIBc4FAZyBQGgiUCwTKAWILZmBOFGJCf+XMqIxvI4eCxgyFaALiunVGCa61'
    'Prxxl5OJ/a+vd9bpz09jhL++BoevFrXDl8AB8CuGHm0Z8p3xQvTt3Lfn56+v2iHjXj8Vnj7f'
    'AAXPUMEzWDAB+8AvjcpdRiRqEfxIk9C5SejcJPTBJqFLk1DUZCCdE412S+p7hD5/+AjhHv2k'
    'e5ihSj5R3gWXEOTcsatJhgi6YAUmTNrMjOZbWq1Gzy4xSfP5zqsLXxavle9zZs3q5sCWBw1c'
    'vU7MuqSVgEiR2RmMTxBcCiB/e/4I3rHzF0uXx+s/mU03obt2Z7dBynP7I4uFN6s+6Y0G989h'
    'jX2B69D2X+v4PQ5mfgxwsh5zTYWrz7ntRsmlcfeDPykj8vIyG9k/J7FGJyY8SptNNZHOmA2P'
    'dn3+w03+8MEmf3ivyftrF1fLSM7VqpL99VL72wdilnH1r09PN0c1PX27YYb08lXKZbkEQ2Jj'
    '6Lpc+vyvC4aPiXbVanh+U7g5JXn4Od3ijUhI3r5/kMv3LQx/RBp8VBg8UgPxuS5/WfTnL535'
    '/5ZjnQIN4iuCzYUzoqufw0D2zYLF7fmIQd338+2DUvlrjtGb8FUoGaIR/GCm+73d3VGH7t6J'
    '8sd3dyeE+b7Dka5C5WEOZnh/ji2om3j6xKffG9Zb7i48w0eAv87Y0xwpuwk6AnE5d9EHfiel'
    'JioZQruTPvRT4e+vuXuBX/9+/S465e29R48gfAT6jz/++KldsLVwZ0BE/cANUhlddBnRF1h0'
    'cJ6D7L8QgqBpcKvv3cIvhUJYOvl+Ve2TvCkLavjLjmheTjivHF6XGu59twTbjjIwApZlVYNT'
    '7GCTQnSr8KdgM2HYhlCwPd1hjj6Tvb4Gw//PfzK6dwWhUNy4epQHEB1FITjc87/+lVfyt0K0'
    'QBa/DebtMZiq3r/+9fLy8s9/+lae/yx+G3D3v/519J/6fQmKeMFHW/jXv05hSXkTFzS91+Mv'
    '4OXLp4hBN4ZRZJnLIZzJrkGWOQUzOC7vl2SC1a89E2xCjr+9hVd/xSV+KsRBbP/7p5XhFtwg'
    'tBvQPhAW4bG0v/6aRDl//TW+PCAIoYVvbJf1H9qSLxG44BJmOr98tFMkqHKWYfE5g8HwBM9D'
    's8DYfEqVKQY0FIK9G3YUA2aSPoTlbZPh4mH0x0mVFeGTj1EI9+WCwnPB87vFMdEAxng7/tsg'
    'Z9p2ZMf1reaff1YOz7/++ilSpcG5P4EZH7BoUibkheA4hpu6TLRn0G/p5dOnkCTFgCN9mn4u'
    'xHAvYLJkkH3i87L/SfX8nvgD8CnANBiEX3+NNpD98hQ2KDma+uRD8lELbJsrmqUA+iig4RNf'
    'dQYbc2L2joh4NTThjhgf3EH2acIK0eXB/Es4iz9d9mTEn2zPTj5yovwpOHW54FqqKrPJ/o2d'
    'a/i9Yezg8Vv4JalgnKs6hiLo8kmI6nNUOFLoOAGRfL8SLtGb178XfhA4ifFHng+Ew5tqGKZg'
    'fUpOhUkuEXrKKZQsfvxy/bIcvww2iUfGSrQP+wkCwMoXoPIFatBQJbw2p/UU36sRuPI/ggBQ'
    'r1Z//FxoxmHrj92k8zSo2mi7h852KgqXS0BLqJRZwsTKdRA/tNz5ADfXc6rCngBiuTZ7FUYg'
    'cEBrkkPtJO8oxQVOc0NG1pgXKecntLZpNbZCt19GlBHhEI1KrVLRqkqV7q26bfbUbrNtd88b'
    'SA+c+OZhdTGityNTHxwAgW/RxlHXeH0hoVYMjqg26KpHqcLaqRAWOCSUClWtI5UdWoUa0Hg0'
    'RwTqtCGUvlIabBunzlxvNexTqV0uda0msXeqG7ZVseutGNyBBwb8aT+c4KWRJ9t7qlwFe63S'
    'yIUnnUV92ubIuq6uhus+Vz4t5tMO5TS04cjQhjVHJThgMWe4HWZwfAyuW66PZe3k0nxt1lnA'
    '9VZruLXx5X43oZFtfeN3UK+o4JxrWBV7YQ2rlCyUNJys1QSARHolDJUdA6mjxxgcIHQJB92I'
    'SwQameYIJ5rDtuUwiLoWx67S0mZztW55Noxy4rhcPehzegtAe88RwFJp01HHa3c2nSjKIAa3'
    'tjvDKqQ0qdJ62CcF1SnZ/fJuLFXKy2aVwsvD3nwkDlsKM8NNSq8jrZO4txWVU90xjXX3fWNf'
    'BlmAhWNwO0PqNU7d7YogpfFMrjbpqYkSvc0W0pbHSo1nqaEnnGgQRrrtUxmUe/xks6CRoVnr'
    'eqvT1KoeGrrLtZLO7nbr1kImj8M1eqhRB7dr4d7cGWlNYSAvRtDKHE7WK3HHy3WDlq1dTyCt'
    'AVBBqKG55Ba14alnVvqk2HAS2g3UGYNLRNUbT3i2qmy7fWGOKzaMOIvDcTikaOJYG83sMryX'
    'GbHfVk7DoeeZo+EJWdSXu8GM1OnxrmfE4CzlsACU3pjXIAezl6uyyRsDzcErhxHbMTyRdiVV'
    'Wikmbc6ndaFWxafKqumwY8xBex2ki3tiZ9DbDhJwRHk6Q1l27+OBzNZmv9kkzFofwPdTl3Sr'
    'cE0wlW2t1BkccHgH9SbMgibZY8dy5dm0qrmtfp0nMRswtBgczOlmU2c5sANhc+3QQ7cKj5F9'
    'ZjfEhpNRbWxrens2VfsLEAIPCAbXtuJ+RM6UGtY/YkzlSLVXijs8DmNwritWR3BZl1qqrXcW'
    'YpM1BWwxqgOdldJYY+aUmbHwqCzNaGO9kRBem4E6B8ktS18cCMZsMBoN1YFDIgLa7c7GpLTu'
    'vEm1/FZ6+IhZGZ3+HANRgySl2oYtV9Y1RmlPe+1jf1qnFuahKXUkS+0N6l3UbYIq1aFgMwbn'
    'LabSEOUVGJwpAFMjO2UTRTjLGAIdqiTCZZOqKQRaWneNgSGXy42D0NwALYQ/IEK1BPeJUrtZ'
    '7hBMJwY3klvK1KSwxXyOUQom7EanttDrHffUjGKEpghvfCu3uaqqTV51xM5x4IoeXKWaxIFr'
    'adCQJQGlflz0iBicbHg0NbSlw0Dpr7bdieCSlj2ajYfcrMe5CKYrG7IBzGtbU+kYNL+vGd3K'
    'Cti2tzaG7HayTPZAajXdJp1FKlBLU6ac4rTWXXK2HiAEvLCQzqkk2qfRWN7ivNHxh12s91od'
    'fYHAlKU39nVqRaIepE0h9bglSqO9HoMbjOwtR4H9Cdk8CdXVTGmvxlqf8fAaRh0qR74xkyB4'
    'MCLW9gS1Ebo54NuM2SYH8MC0+D7T2ff3E2FSFmNwfE3czNpzpTfzSGDF7LvLKU72xWEFFybm'
    'VOvP+hQkDk1932ZK+t70pN30NJ2i837V8ycH7NozdG30DDAGN/FI6jCkRRnpEQJXV6ijOjgK'
    'U8VoAybd2Ywqa1Vnti1vZJkiIFWXEIVOSibKEKXtCN67JVQ7etCWSNjYmizdGaoi+ATpVAa8'
    'wmgEMu/CnQVVHbcP1Z63N3a1LUT1KbE1w7Z8D8d3awKDxgoyELl1cwWhgzGJlBNN5titQ9Ot'
    'KvIK0fkywyK9E9ilPYjzgNOAJ9fGaTTYKKbdO3UxrSf06jV4wFdadq9GAsCGxIfd+UQWGjG4'
    'OkuuVrTNDzBgSFHHNr23EQvv8D3N7uOyP43rkoKAo67SIMeE3qZGHRzDIB3kqfJsPazMx44o'
    'TJbdSSJRxiQj4FNQ2M6xtultTVi2IHc9qAvN/nQF+50EKqud1h21vWHnSEwpoeUIBLVTDojE'
    'qdV+V5x79khfxeA6jgKX6qVpjWpPGQzTppuu11G00WpeMTaQNFqtHJECdZ21easkCCtfzPIA'
    'JNak1cSt90FL0aa9KU8mkwyEycW8V9rSzMnTqxThHYSjLUumoerUTNrZkq+5mzRuVsRhH+xs'
    'VvZyOHeA4QBgaVtZAz6dJEpGsES4H4ciofHVw+7g2eyE8NbT8Uo9TBfLli6S61O7MgIoiejg'
    'ElOr9BSeHg4FUfaxH3Yqp6W9x8iyVNF6wD4GR81dlZLVxVJx5/5MnK8mKgYzrkgfjgNlAc/m'
    'NGJ3mj1jjOvUSFFUo0Y1oMMI6qx726kASfPN8LATlTO4wZxizNXBXDf4CrbqOEtkgQBo6wAD'
    'Vdur2jYMLbEpfFhtN23TYhfaAtqfRPmkkrsSwHCLstCBtfIuGYoGf8TMJYFtOBBZttCpbwlY'
    'dYDuWmKHqc8IBCdnem3OsV3fXqZtekPBRwfqmOhacI5yfySpDNasNLlFDK5vVRp9WuoOHX1z'
    'kk5aiQDsDUj21SEjtlzGsyiUYgCteiT6xkItkxQyru4H5eHKpAkW2R0GR2O+AbhNDG4Mk6jS'
    'BA3IUCGx1D+oElQHNzahSWMbpRG3Ta0AixnvSguM1EZlGcBH2lbG1IWOsDutySJMow/vtsvE'
    'Rpm0NiolVEdqo0MOSE92vf2i3225ZXUrc4jhGzSk70sdkR2hlJjVcGxglrfvzAlruSYHjOas'
    'N42RcUgYhR+IpNnqNec7EGXp0kgdiq5SNaByU6jLHmPMmVZrBQuD1b4yq1jmCCYmBm9g/U3F'
    '6et4SaYWh8HAMWYxOI2p+S8nws4+Lhb1lijSR6LVL60bvdqI6mPSrjKf+dPSPWr78gnccdVd'
    'td9ssLNldUCXlQaysCCWoo1+oslaA6lXLy+OxzmIaeAaYgelfd081EvArjItibShmgdFby+E'
    'hQRAU8q3t6jRtgPtnZ1Th6UDofOMNUYTo6JCraymRZcAYjbp7KsNtukSbUfdOD1+WsWrQnlc'
    'GvehI0WNeuuxixzUlY25ysaolzF85djTQafkSvBYjsE5EiqYHRfYUQyOdSbG7qh20BE6WZcR'
    'Qm4DiCfK4xINVJvd2mJQ3fv2UmfVKldJRKWVMexN+X1jsK2AifjUWLFfqqBQq42RqNyvdFcr'
    'EgFsZ0bX5UoJ6OHHSRsjttW2xkLVpeT1lNYYmwNCZaOudktgDjLrITXvJ3q2tlds1p16swU3'
    'VmrdoTAQsNWyexjXB+CxQgM1urwDncr2BCJmY7kZtddTF3AME2/MuIoEYLtGe0Q2qmoMjm22'
    '8XEFa0FbbQlz7hbtSyq9YfZiq930xa4hY5UqNtRNRWp1bLcz52rWRLHQUU3tjXfiusfTC0Ku'
    'DysxuKUBC+xc3sP7I8iCBkEtxgrDdxvUeNzstSVZ6NE7qd4DgW7XgLqrwWB57GjEbgRDXUk+'
    'DXZ9ylPQ/RRKJApha2WJgcHSUXFtAxB7pw49Fkpji8Un2zbswABO8j16bsy7vNFW+23EXKwP'
    'CD8zUENyaBdlDlQFSTqrlCmsLqxG3Ta3GMFVD171N0cCCYygKVWDNEoHhzUIsWd9YLAYi9hJ'
    'm+KD9kn1cGTM8HNx3a/VdHWaGBXtRa/BQHB/3QEIwls2mL6lM0d3rrZxu8LqkIuOhZmFDjqq'
    'Mx1VvXZ1ipQXuMJp5fl6MKz00fFu2xpOqwl23rLFSrRSFqid6ssGSZht6/Zs2edVqtccn+gd'
    '31psBmvWnm6aHMKD+rDj+41EdS9pp4moSfyGNNewlNjGvGlMFU7sDsw10RoN6m3a2x1ko7Ot'
    '7korRDRbjOMu9o0+U52up9rwaHYcVNIHrdGRnLYJQK1uVgt0TMXgmMVijkJE262ehsy0Mqft'
    '6XDcHNSYna32RbPnTQ69NtTbSU2KmwsTBjCs9lYy67351tvull0FQN0JR/USo6JvqpuWTumd'
    'kQPxEuP0pgwAWLN511hZs4N3aIMmSJY5rgWPRgqqzY5wY4Vg62WPOx2JPT9cYnBX4fBEV+CM'
    'C1a42nyzNBoVo+s0y7IpdvT13jdU5zg2nswq3VIdJ3SnAo16tS4m9tYbajPEV1CDACSX6paI'
    'XjfxK9DO+MB0VxDJ7ClStQa7qiU32h6GCkd0Y47bcw7TdwuSGasTvrWr9ze+IePWJLE5NNaC'
    'd9LQXWWzXi3PxizJyK1ZXcZ3u91Uog8jvo6I8ma9I8rDfmVVFVHKglYUWSfrVKvHVpqwS8It'
    'mXak2cqsEbMmvxDWHTpOzn/CzdFxrpXG6267ax6sztbuekiFW9da/VWj1PcUUWm2SK0nwVMR'
    'oHbaEoSb7GRXZ8rUnmq2rYrvxYiddiKglp0Df1wtBkNf0ffBOb4edyRFYfvD6Rbe9Acg3yPw'
    '3pCukwe1ym7r/apqKysFXC6t4wAuC1O0h1jtQZOOwUl9dunItRYz7QOdXttTcLtjNMDNYGJK'
    '04ozIGRfkxM1pePWt9tts1EvWxQn7Vxnh+hwpevOOLXNl8TEqOB6m+Our6wlvDG3q/CC75lV'
    'jZ+bAFUVYHjGDzaOtDqBzN7mMbRVmrLQoLuQ++Ia0cb6qeV0dz2QE6DENt6JMAI4zQlSM5d+'
    'LwfAgjjZjObtJLjvs/hkDsuyiZ5qu/YKn5wsyRaXvve3AbvHMsdibXe0sEm9bCfW53y+JWWh'
    'NoMdo4PJpjY3V956tISHGlMtDffb8VJc1LbDwUGYcKOq3RfJXmsuYFYdWywn9VXbI9dz+zAl'
    'E/uO3SroEMBXEjB0DtSREnGCF4kps7D2Ilg70kjVmnQgTl43TRWvgcaUpkyx15C8g0w6ixnX'
    'nY63m0ozBkcarM/F1tGxEASertempPhyuF3eMsYKBl1nuWjL3HK0FAc0zpZ4sUfWB32xQ3Q7'
    'iowPTKDR3O7Hs+k4YePGujLqV9mjL7prGsxLsy22KK/nwxmqOfac7tN6qQvLpbJbqWiNja41'
    'BL3UEDbdRclXnbVSFYCXBxHuxuB0cOxJ5RZeBZV5Z0MoM7t9oBtDYOE25LldajoTe66o8151'
    'MLeYiYfJ5akKAXPZGUEjtDXCHH6vQoqRmNoHdWmasO/NoWh7TR2WK+TozOmVUK/PFlB7uZih'
    'NHOkp6baWRqmsNJAq42Vpk6dno5IfrPsw/PV0ATXSgzOFmt9fX5isOlojcFcf7w1Zmi7Jajt'
    'drU2amt9aIkTKwPXjhvYXCuePVZ3U9nZz6F9b9DtCFsFV/YynIhP0UGqrLraw1Rluwa6lMVv'
    '+31AXauM12aN+RgHsEkDPrgyctie1ot6va0rVaq7nLhwZwDprcnOm5QhfJdEKhhSVul569So'
    'U3trNS6TYJ1pURsEbR5X7b6jNBaSBMqiBehok+OYGjBraN1mkzIoYV6rasKqAQpWJZEovuFA'
    '2CQiIpMFjp6UWpUUhj26F7ikZo8ER8yJGvT2E4NAV7i6A9j+gTwcvBOO1uReizwpfXuu1/ti'
    'wnc8LR4cVUX56Vywlv2KWbL5aQWq4UeKM2WcXnaJacOgSYeoHNcgtYVH+0qvfDqhLaBp2jug'
    'fqoYqChvzz7ZeEfvJ4jv/tMOtmgoCNWqNnzUrKPQsTDAlda0gVU6vqlO4fvVuFGqHrat+Xqm'
    'AlhzRHiKTJfqEnsW7tbSa0/r6rGt1ZcNm0EgsTotl6uoAY+d1Wxsobiv2GcO09JsDBa6faqK'
    '9OqiVAW3TQrmyovltl+lq4n12R3gp644ZZfbHbBqVynfRWh2KMx0x02xRPZlDmvixunQAa1u'
    'r3UwN1MIp/doHR3USU2sVwaKPiFm9XJiG896bhuZIsxRZVByt2d02oSVXp1lhf7c8Tmis593'
    '6it3ZBAr3oA5QGXauNU9bbe4ikyaJGCAti/N+okVcKRmSodAmtNFAyKa9IhbjhcDtYLs6laV'
    'FC0X7i3nQmc5ZH0PVFFaxmK0qw7sDkPUWHvR3TH0bNVardDEvvP6LrKFEM0zurXegsT0Kreo'
    'NgdttCHSo7HYm7sGz7Yr+62NTfs7vouz/SVTtRpopdIYnBYTncP33RUBxOCgw3w93OEncVJd'
    'qQA8m4xhfrYRWtKa2J102tWGSlPcbyZVcnNQXaa2GSKE5zP8tj/qWstauVeusuy4nGDXOJQq'
    'vMF03YPQmm7KJcc3hEkPRG3dI+0dNICaoxO7IQ1s3bB5+rQC6coSORIQbpdQsTnmKOikHBqn'
    'RFdQ9Ii19ZFyMnpcW+yZGMZsj2V2UNfR1cjr8/gWZrdbnd+ic1TdYNhibhgdmFlKa2mhavND'
    '7zQct6tmwsZMe2W1Fe+4t9mFemgZ1TlSaejussoQBArZy33fbfAznoXq3pifa/xWIIboZEGD'
    'pqgZ+IGtrR144jUSAYWOZwg5PM2wylhyOjWihlZrpG4OIYnZq5UD7iCtilmnlKFiE9vjQeSn'
    'h6Gw1n37EWKA5qJBOhArD47rRBo79G5PweWWb7o2u9s9vKmDFoxRbbvGruDptEKs15jLK16X'
    'gshWdWpTTWvL8bi1AlRs0fVNhupJ27RqMbjmuk9IIkvVGJJvVNQmxdb7J20+Lg3gCmxqLaJb'
    '3QC+QTwZVQyNIUQI6C5J5bjSEABEd3UbaM90Zr5M3OPlSLHMPkAubRNWl4v92O4RFoPjcLO+'
    'rW59v1lZOBAzhOcmCC1hV/WOpLdvVpj9zgHt8XRvVcuwKhuJvFOmJgGB1Z0gT9eIggx9g7FG'
    '99asOCDNydKpKcpihB8QtDYFO76lhzbVwWZUWi8GPvda9SqP2L44d7qJ6iktJpqJqA15VTNP'
    'noOuVrtWeYDJ7gGFsBk0XUKWaFgGgswqB8wB2yMDgO0yXy9PRjXjqOGVHYqxeylx8SxHOyzs'
    'MuqiHlnBBcugVGNbshYAMW9VjIPBkhqISJBuYg1kjehr3/OFKHy0nyx6IjeDIdyS1g61ryeT'
    'TO6WSxhNNaaOajqo0+3C42H7UNd08nRC2HHdZeY4yuIOAaHzrS4i1H4319dqZ9cR5zixYLok'
    'S7RriU9GIOL41C8P95x1GO/VJWowOKRMJit9zAx6gDKtrWV9fDCRdbk6gaviEDCHhDEw2nV7'
    'L0+PRmWwU1SXTyz3Hoc353h/Lc+V1baiVk9rtEUhgzo2BesojLXGorfnm32vvR5J5V6lxywm'
    'jKBBwfKYXd6JUmftjeZN4WzyCNNJBQRZ04Rmq7YuwZtxFVtO20ZFE/vt3X7aGbr8zuQAYUYO'
    'JdYxMaPLDhAUWZmEV1kxtf1S2LGoG4NbcVR7MaJwbALic7cLENMttvNAsoUdSqU5NS+Z2GqA'
    'LIxaR2zQG/bYHhydZseEB2MFbPV2KAo6JeqEJzEoDq9PdAWH4Rqxl/vq0tJcYY0Ra3W48VVZ'
    'Q4IM6biiia3ADyigg/Wx7c6RnAVWb53U2qnbtAfjuefQiXB3F0PVNcnTkbNkejU9VYDVnHSr'
    'iO2KOtJdVrtoW2AYgtsxwMZ1Om2gwzZHB4ipCV6Z509TdtAm1oR7SkTAYMqpSqVkMvsKWEMI'
    'q+3p6yG/x08+TRbMulZiO91VZWnC7OTomI3e0rBFdogZpm8GS/ZhDW9IFl4nEbJN/eQ2NlKz'
    'Ph8ibRnvgkxDHhsb35WZE84YA7scX9XKM8RttVYYSUFtrW30WW8+kbY8vKmR0naONpBpgt1m'
    '5MLLhTDZqW2vXd6gxMiVgcYWGOoih59sWPQOJib0wSZFThelCgG1B4ilc03vUOtYLrZc0Cup'
    'UvKSOeuUpuLcoMDBilnsDXxpEVCd51yjBvTkhi2C3GqLLKsQI3VIlp1iDHboaLOWcvSgqX1c'
    '2EeRXLWp/YxJhgJ0mrvNrlGaQkq9dBArPAUxGH40SgCu1NDVUu72q25nglo0AcFHUu/W+QPq'
    'CfhSH623B6QaBHzWo8RcnFTGW7hTwfjdzBhhYPNQWVmqW6vZ7caUOW1ONObsdGrK7qpetbTz'
    '+bcz6PBVYdY1IFrc7+iJyIEyMUhWoiqy7pTYGqRPKzBTdTb6DN80B315ZFZXjD2cLZeOR8gU'
    'spzvEKVmUc52u+JMCijPGrV9c4HP0fEenEBJhAwx2w1rsIcHvrqrTWDrYLmrNb05LKiF2hGF'
    'jmTZiMyRo6m5K8mc1VNAXrW6ZdGWOLHRmMgzdVlxlmQSrNza+1ltXeM0q0TUKIur4doa7y9m'
    'Y4m1SGy4972NvlB2NWlV6W43yGE1JcbcfFc1maG0LknjmSaseQ6fJ6a21NrBTcg56JPqrLPt'
    '1KghfGxUELuPTmVv4lUGOn8Al77bNq3qrcOi1iQaNFpCiLYwHLmILNdGg46iJ24KIC2PU25t'
    'ztfLCYBtZ2O8VOqYnjimGVZmN4fjWKw7lrfQRsTOYNtgb2I7fcNcj0xCYuj9uEXvu5PhItGz'
    'e2NeGynHWX+FL1RXHYGuAmJ9ssJMNuVT0y1v1BpDwMO5yu1nJb5sqevmUeewHS6sF4I9oeYT'
    'QGbZZWJ91o5rTrUGRF8bGsDSl0GneXfPztYAYfQMuNzeunqD9F2Z3QlY+oqr7rMPz4AQsOtw'
    '+I6xtxbpi7vTKcGu2ikP+ouBuNt0TbC3UtS6Z7Xl9nIplBeT6aojmEetQ1Xrvm3HeBV5KfaP'
    'SxeiYXTmNOtdiW8ATJk0uURANcm5QvWOqowOMQhRHZXS6j0acDmnqjsbQ5+27DkO+rZnD2e6'
    'm+ZiTK/MlXFSlMoRbQRB12p9NVyRyYoAOpRH7SozakKjsguM1kR32ARXk754XJQcCtKcwXFg'
    'SY2VZRgrdA0zrGauTpMxu6wxVVrdWvOqwR2rtSTwYbHbo7Pj+h4CH3aDbnPkHuSmaG9Pnjc6'
    'DYwDDZKHZWe1t3UB3E91vl6jj1z/YAJzRKwb9QldUhFWmiSTrLX03fwaXV7DLZx1+hKKO31V'
    'XdouCkriorkl255w7Ak0OeObe5SFKqWavplWLHfEYj3HXUH41Bvt14kjsKgii+aSPNgA6JPR'
    'XU1avqI5QcaI7jNH+wS6zKo2sX25jkMGq1ZK1m7TKu0ta4FUAErdNogBsiJWvUQxrhr1w2CN'
    'c6sTNN1B3oSeWrOWMDus6vPuYA/MW3rf7pbmxrgv6WZlVq+rtuvZ5GgmzQcihFF14OhNN2AS'
    '0iIRCBopCxDFSLVVBplK6aDUze5qbtAnrgssJ5XZVuLGpeMG65fmG48CVaBi0X2grhJgH500'
    'oKq8W/ST2OeWWu8tHlOsjT+ojttS9bk644/UoN/qDLHNBtdsh58L032/VXGrp9nw2CPMTpnR'
    'avuS4bW6A5SW1OomMSrGO7KPAd1qXVmUq8Bs481mx0ajXKoIx1kbKntG21TN+RFhTqw+3416'
    '7Z4DVBhtD+oCR/QxzB7iAqGfV6KUrkLR604fITWP3DZaQA+W9saxW291u8O978rOFXPJqeMd'
    'z3WZwWRLykPGnK9OLRavDbXOuNMcW/NDN5lkS8VxRW2527G7HqpW0PXakxGBQGgNaraGAlGn'
    'FxYu0nV22yecKsxsJxrrTQ0Y2k6mLWTPW7vyCYXPC1vIZNNzVI5153KtRyP1XWPRkwQSOg0l'
    'ETBZ8+iQ/rxn9lyr16PKlLiZLVucuHSOvo0HIWDFObiNLVFJOrt1pocui0C0MxzOieGYHuMa'
    'wFJwHzOPC6q3qoM7ztcH2LFG2NNpY1qdKSArYZTj1XoWoLE1U13ONloiApzWvA1OZaAiKYg8'
    'AcHDvqGRy1HrqJFbeGuXJXyClOnasNJSG2wTpueq0Jcoo4yVDv2TaO7s0WxxwLkkHLjokore'
    'Hrdr09liVPWYJk+CaImQGpuh3eI0swONIG24FcASs677NvjOIJq15YA67s1dF8HZRsfmuQGV'
    'GBXksms2ra5haZOhb+zUp/ABHY1bVJWmm4xotx2qtBdACj06XWiM9RsDbzpFDg0f7/Zm2dp6'
    '7TmI7UguiZA5PderUBsQcRxK07HO3JbV0QEeCA67rdSnun50q50uz9cluF6bnihZ2dvdMWpg'
    'SHnujFeKu7SpOaQnc7ai9wRh3l2u2XarU0aIOmKCmNyiWhplUmXWOoFDs7XQoMqx08YwE9CZ'
    'hV4RVv0R3muDY2hWoeSWsKHOWVpDipmbFnDwaTFrAOPVegr0a269Sznjo+KeQJOb62gLB1dd'
    'tVSCgDlplVSTF20P6x6g01bxDg1sASbLH7XBdlPBZmNk7JGtPYxX+vtTfd2pn3zva+iLA1eS'
    'avBRFoZ0tyeUphMERbei4xlbegpU222MaZfk0QlLzMX+uCtP6TVXa1fH7W0XJPHjssN32w6z'
    'R4FSY9as8hvKKVWlU2sny6OjM+oBABnkdXGzFTHp2uZh443Z8yTzzHrZdwlHtu9ZO5P9ltgv'
    'DoLn89MBn4nNwVKABk3aVicEBp6cLXoQSifBGDdHO5QRwb5RO0w9TF4ks6K9H8yWHU7E1gcJ'
    '9HSR5laHFl8zN5iOWapdt1aMUC4tMK686PR7G8HR9hMUbu8704XujbC6shUFqXs2Ztm9Bp2W'
    'BGTIJR5XZRfVRWtIqQegU5Yns6qH4Xu1NtkdDv3uFjrp2n69mCHSHJfrvWW1zQMafzB3kpl4'
    'jGUTbQ9VcnWyzephZ7H2jINHk8N0acw2dasBN8cjqjVYDPZkjS01YXe8MyWvt5n48wNCRZej'
    'YAM9SttkKGx4i3bdkUeANVyhZ2USXHjgZrkA990yYDh4DQOprW+irrUB60Izo9w70DKLD5c1'
    'erh218SptGkfnFoSlpnhkneaToZiw6AXx7WnWhxSbuy3o25b7CxXToeb0gN6rO49ERcrXVWu'
    '0EB5P+yby0l3NqWrSx4dDXg5iX0i8kZpDAYtWVYUnB5DE7/zzFIhB95sSamj2rgzHGI0yUrc'
    '+kS1FhA4WQA7i9mbzSqgnZRy1d7XRN/wShxQqqzP1tgcPpntendHK3Nw3UF7SpnvLWe7pYAY'
    '7KY27E9ZzqRVjJSVjoyUZBSrTZFTn5zOm7thgzYb08Tkwal51wYnQLlb9wBUARtg2WAqbk+o'
    'G9sp3TTp2nw+np2IzrY2nLU78yPRRUnPsZ2ejOx877k78qVlJ9Gzs6HEHcrs2l7MCaDfA/U6'
    'PMbqGDBu16FDDRmNG7zp25zrlkAvRpNO2TcPOhyG1i2gfGpZ6m52QgfYBE9slO1xOaQlR240'
    'evxoMq1olcWuX2oPZW+kUPBwyy4aniAM10t1PCOrS+ZorlvyxpyTItSeTuFKb0c2JuYycY9x'
    'dr1fsbDdWQzX1SXJA0rH8GWW0e2Xpou24Kxx2QCXRxzr4HC5BQ/Mxn6gdvTDduhAyBR0zQku'
    '4i4xisENh92lSo/pSdtbnGYWXNv31k57DHU1fdBzqyJRHc9FoiEPl2QZo8gjTPgypLPrH01p'
    'bZQpp8JahCTzbJJ8Q2iG3ASkmWOxC6LMoXALK0k00RxZomDL27YyR2EctQ4aZAB1E9uYwniq'
    'NhlpuehRI3Qv6Y2VPGQTF6/THu7E2co35nXiOOqAlr1CCV+GEyeNWukjr06LHtfQVqZdGdXd'
    'JrF0WXSKUNhIbc0UTcFHW5ex1U0Sg5oPdWFwmEkb3Kz79vaIqCzHp7INk2qzD1gcXJ+7nW6b'
    'mopTU1m1Z57dbpvV44mAV02ypMEUcBqK6JFI/Fnl6M8yZYBaM0EvjU5gaSlRFeCAT6rCeLPc'
    'kZ7ULiFjTN01B81NB+fbIwmdEOa+48K4UKaW9b69Goins3CvmY3G0imBhy7TB7uNtuZtRKhy'
    '8K3smqCQhlwGIHpa6ymHCVkbdVSlOq57077T8zkOhERtN4d6fbWc0K43aph0CZJIadaYrRm4'
    'epiSvjWqQbPWEZF447CTtKEJ7nfqTmU2C2bdqdZtbVfqIrSKQGZjbjN9bAoQ57wAnbPGYwcd'
    'Iga00rdi1cHggTJzbIQdL1u4u6X3ZUgesIbcqG0lxxhILthSbGKwboEojjR0Z6VRzSSdD4PA'
    '8pIT9gKNnAYLuDTwCHq6MV12zSFqA3OrVV4mCWZdsnclGBmphLcCJA7Y0YxI2iVyB5a7DM3X'
    'EgEFCZSznkH1lldXWIYcQeps1y1ZjHFc+zPyVBeFJjs/LWtoFV+DY8A6LhZm31fHOEUtZ6Vy'
    'ebft20PTSpJvRpZWlsnjuLpSeWc27w4nXa5GCjULWx0rvRXjdGYIvdi1K8LeA+fr8t618DLg'
    'uvwMJdqGJe58yKX9WfUsOBEi5BNeOiLHxn5YFbyjWqmMlTFFYVR7VRdlYFvxjRAX0ga6L+mW'
    'kxZAeBucMbktNdurw7bv1Q5byXLv0cK3hF5ZNTb8GmcZ4WDbbZFROJsW9vSe7AId0leHTbk9'
    'EHogAVOdoeH78FteOFGALs6EiYmd6jCY2HdebcSgGNXZWwwE6sriVB5VUfjQ8E5DryvBG9og'
    'hI1q9epTai9RPNmtTfoYbM26LD+ulWYk0odXyHCQSJRWf+/bf/ONIG/a4pCvjpqOCW/ZeWmm'
    '9WRKw33Zjro1qCnjJYrtD8bYvqfjAnuARb26BeslWFtpmAwngQ+ltJV4uIdO242B5e77IEMv'
    'Ibo09FoyS47UCuJr2BKlHY4Szeo93uQ7R9rpD5uQRiMDWdHqA6Y1PXUSN6U+7TfbhNUhxtva'
    'ml2JRq/LVLsThJvPSG43VccnnFQqSnciSLWK6qA6vNCbyw6KbAbSoSrAah/q4NMZlyS5TkSy'
    'vl03QVvblGAc8uV0a6ACWwzvgmhv3qgvhiWkI/yf9r61LXFlWfg7v4LjPvMQFoyIqKB7Oed4'
    'QUVRmRHv4+HhkkAEEkzCzVn+99PVt3QnnYDOmvWufd69nr3HkPSlurqqurq6umptMjg7nt1c'
    'ff3a79aPEJHMOrn2w9FZ7zW/5fWmdbZWXBp7l4NOrlV4+XaYOTs8tCdOdZ4/NY8e7A3jst4x'
    'zbaFtsJrw73K9lWr93qD9hKZ/TUjV+7fF/Jnler63WQ+srhSUZ6WSn3v5vA1f7M1zaxnvHHr'
    'dnvc6hYmxZxe6N0fHraPjWd38PXb2utFa+s27xU6hdbt2Nvc9rrPD8XB2nVue8BU7bFhbGx1'
    'iq168XL7pFh80A1jmLvoFOu5e/3utXg/Pnp1rerGtn6TPyqtr3093Ri/Hs1Lt62cN6mvbVWL'
    'tUMvY0zYhQjnIZcxqoez+1rxZZCzMqP8dq042q6jQU9yhbv1YrtVfNjeHo8uS4X+pD4rlTo1'
    'Ey2x40zGuHnNeUet0va41mHXNXSjWt98GHdK45vaaw5Uzemxu1mo3rbOXr1c/lmf5GqZmmdN'
    '1ouDLaOuF8vW5rByUhygbVVmWCxOO7WCU3jQuWU2b0xqm5mN9btNNI7p+PAlY6znnFK5Ni+t'
    'Z2rbm8Vce6tjTE6c+WurU9ufbJfQnnN7LZ8zZnYpN2kOM4W2xwwftYk7Xd8ct43Wc3+jUixs'
    '5A2k/hqj5/wE7c6ahlEwO9v5TEmvVXtb+tHEzJ3eZNqTza3pdi43qWZKpbvOZs5g+p01yZVy'
    '7klrXmznapaXK90erm9WDTRhmfpdYWNjvfCiT8xBRndP9kb6bTV3v35xM9etrQcE+FpmuNWx'
    'NjczOUYor2ijBV5U3ijnPmzWSvlMfT/3Mu6YpRPLet1q12cbOYTfjWFRnxiTeQmtRNfF6vbm'
    '8eSuMCpZz6Xx9HQvZ7CTKMPIuYWvmUmp19k8Hhqz7rYxeMlUO/P19qRaKF7WirNioZDbNE6P'
    'MoZztuHltntjq/0wyU2s/loul3ke5Nqv2wx3xqTovc7ak9KwlHs93TJydw+TZibzsFfV72rW'
    '8zTjnlgn25f92sUsk9OPWwaa4X5h8rDRLjrzq+1ivYjGmtEZoRxtlIzadrGzfX1evS0Y0/Oh'
    'U5s6d/NKobp27E5nx4O5WxvU3edzwz6356ezawdpHxv7xc7B3aVnll+nxdzzQZvZPoeZ9sbc'
    'OKwjUXF461Yvq73rh/m8cnrdnn6dXj1Xj4ebo9vj64uD8nPdMffn3Wnv5no+PizvH9kHo8LZ'
    'c+b+tde02VWX0Z09zfW/XW+Y+qDc753f9Psvr7OvvW8PB9cHdbNyfbbZmVWHRW+S6xQfqmsZ'
    'qzVbq3XGzen2oHz3/Hz+bVgu3XTZSdSr2c+P9qbfvl1fnq+V7M5oVj47ODJOXw9rW/uD09Zw'
    'ePByt/+ct/P9++r8dYh2Q1eTu9a36va4uDHMvFQvMk67vMYO8ueds8vjm7X9o/1n6/gid9Y9'
    '+XqUqR4M1/eOasebg07h4jmf6a/1Du+fp6ctCy0A04NMabO1nt9yylc3x9Ozou3UK0ze7Z+V'
    '1qfT6u1B89B5KDvVF6SznhX2Wue34+58XPSm9vhl/2WzfnVw880dbiB1pDQ57nX3zPzl/P76'
    'pOyV926dqw1mN+6b+/v2pLVfHhzq+z23fTt4Of6Wv+jny/sbF5Xya+b+oHI8GxwhkTl+WD95'
    'npy9OEftb5mHw0ndWC9vXp+95Nptjymzg9lJv6kf39ye1grm9tip35zXT84y3kanUtBP1zqF'
    'zNfO5nrhdKLvj8ovw9etztdZ57j7cuAcFCZfT057mcr8a63L9hXTe6c2LM9G9wfu5cH55Kxf'
    'OyjsV17s4e3ttDMZHLY79avB1sG3/b1++9ZxPfugPy9fWw8bN97zuXVYqrbPj0+mQ2apaFX0'
    'rb55dNU8u9rYszP9rdM142RmPFSGurk1MjfKhn1R3Z4Op9Xc3egwPzXOD66db2s927sdXax9'
    'vd2/2DtCSzQj4wN7e8/Z7nhot2ZWXpqno7pemxvudaV6eNba29DLd6XLvXLpXB8eeqNzY3Z0'
    'Mj1un7r3985dtX63Zs8uzqvz03O2TdmvnJ/ppaMX22ruXT/ffHWftyoDe7hXctuG0c295uq5'
    'TLda1deuTgdfO80uUomvSpXJvt6+QjvIg9dpweq4+TNmma3P59V8u3J8dTTY7N8MzPrxfLMy'
    'ah13r+ab7cuT81GvYhxvFB5alrO2YdW3jMKd2+zn8j27eTlfv6uuHaF9mecy00JpT786Ojs7'
    'qzje6Na7HLw+XN1mjuze19HxrZs73j+6HHi1vZfR2at7mXE2Nhz3+du9azfvStsbZ/c3Pa89'
    'ztzvzRnuWl759bJ23TqumketnlO4fKn3Nt2989JtuVO7bU0Oj47N81v7qGI0Ow9bw+vDC7u9'
    'dmsfFLtNb23Uz62VTkfFSo5vQG/qz6XWwdZ5qz42b62DdfPwtvbc+mYcnu4/17r7Tv38qlIq'
    '1S8npYv2umfsHbwe7+3t7abSijui5Fap4goou19KfyV5VVUduPjf9AqsTu2+kE225p7uoj9N'
    'Vye3ixvZpKXPPBwUYmyZcJscgmnpcIHfQx/kPhKNBgSEaeB4JNL9WwhOwiNIomd33II/J/Xz'
    'qv9aDHkAJRr4JjAqxv620IrSg5ShpkUCZgg5pJzUdzdjWpBXMJ2YNB1Fgf95bH5+bTzBv2uf'
    'txtPv/1nCiebqqQTiQS5vi0BrZVxWj6I+04un6+srPBX9B5xctqDyA0Q1B9f8vbDltAKfqQF'
    'lrCZhlkY6q6L5iGbHNmuSWLp82BGQtgK3uGqur4YxWxgrLLG0NjZo1xADMwjgIamm7Ys9D10'
    'u2JcNFy/6XRdKdiN1G0guw6p/8lNNhFRQp4F9Ni2B+OhhZ5SyU9JRR4zt5uV28TRvOQ3+acw'
    'CDCicPcZgN9k3fGCoRxXbpfTQIMRwQGNthCigxEqFi6+DzEZosqyGFb4ijYPYUWjbCDW5O94'
    'Na8nhKjF+Gc/OqZDwtWK9fCw0jQaUUIYmlyq0cBQNxqr+D2Ag9vy4wWjHrJ+0IHdcCf4vc+s'
    'YnSZQGnxU5jHNLv1rLe99A6nQxyzgXcBST4SvjyAuC6NloM+uJA/+ccPQWCkdKsjfHt7E7/R'
    '6/E7VCySL29yp7qFRBuJZZgaewZdkNlX0+rpjumxQKRRHM1jIQhByXxE0uvyXrPdH+gTfUBe'
    'hAMISfgklQJw0LfAUA3bMFzd211TNITzMumQlykoUzAbUGhxTFT8lBCC0kHgBb++lBecv41I'
    'DO5/300SkRGa2Ud5NmOj6UW1IMx4bL4MRHE6LIm6pfmgpSHMzzoJtDEYKJImmEiaIxittu7X'
    'EtdFdbhUnOqYFcd5jnmPgeDD6lGxKDk+k4aKoGkbzbVlGgsiGYdFYeCEs9ssxrLcgBARjFYW'
    '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'
    'l0Zj2DStRiPFTuaEVTid+F+qKU0iNZYBAA==')
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
