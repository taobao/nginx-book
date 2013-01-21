# -*- coding: utf-8 -*-
import os
import os.path as path
import codecs
from docutils.parsers.rst import directives
from docutils import nodes
import sphinx.directives.code as code
import re
from sphinx.util import parselinenos

from number_label import CircleNumbers

def replace_number_label(text):
    def f(mo):
        return u"#"+CircleNumbers[int(mo.group(1))-1]
    return re.sub(r"#{(\d+)}", f, text)

def run(self):
    document = self.state.document
    filename = self.arguments[0]
    #print filename
    if not document.settings.file_insertion_enabled:
        return [document.reporter.warning('File insertion disabled',
                                          line=self.lineno)]
    env = document.settings.env
    if filename.startswith('/') or filename.startswith(os.sep):
        rel_fn = filename[1:]
    else:
        docdir = path.dirname(env.doc2path(env.docname, base=None))
        rel_fn = path.normpath(path.join(docdir, filename))
    fn = path.join(env.srcdir, rel_fn)

    if 'pyobject' in self.options and 'lines' in self.options:
        return [document.reporter.warning(
            'Cannot use both "pyobject" and "lines" options',
            line=self.lineno)]

    encoding = self.options.get('encoding', env.config.source_encoding)
    try:
        f = codecs.open(fn, 'rU', encoding)
        lines = f.readlines()
        f.close()
        # 去掉编码指示
        if fn.endswith(".py") and lines[0].startswith("#") and "coding" in lines[0]:
            lines = lines[1:]
        # 去掉文档说明
        if fn.endswith(".py"):
            if lines[0].startswith('"""'):
                for lineno, line in enumerate(lines[1:]):
                    if line.strip().endswith('"""'):
                        lines = lines[lineno+2:]
                        break
        # 去掉每行末尾空格
        for i in xrange(len(lines)):
            lines[i] = lines[i].rstrip() + "\n"
        
    except (IOError, OSError):
        return [document.reporter.warning(
            'Include file %r not found or reading it failed' % filename,
            line=self.lineno)]
    except UnicodeError:
        return [document.reporter.warning(
            'Encoding %r used for reading included file %r seems to '
            'be wrong, try giving an :encoding: option' %
            (encoding, filename))]

    objectname = self.options.get('pyobject')
    if objectname is not None:
        from sphinx.pycode import ModuleAnalyzer
        analyzer = ModuleAnalyzer.for_file(fn, '')
        tags = analyzer.find_tags()
        if objectname not in tags:
            return [document.reporter.warning(
                'Object named %r not found in include file %r' %
                (objectname, filename), line=self.lineno)]
        else:
            lines = lines[tags[objectname][1]-1 : tags[objectname][2]-1]

    linespec = self.options.get('lines')
    if linespec is not None:
        try:
            linelist = parselinenos(linespec, len(lines))
        except ValueError, err:
            return [document.reporter.warning(str(err), line=self.lineno)]
        lines = [lines[i] for i in linelist]

    startafter = self.options.get('start-after')
    endbefore = self.options.get('end-before')
    if startafter is not None or endbefore is not None:
        use = not startafter
        res = []
        for line in lines:
            if not use and startafter in line:
                use = True
            elif use and endbefore in line:
                use = False
                break
            elif use:
                res.append(line)
        lines = res
        
    section = self.options.get("section")
    if section is not None:
        section = "###%s###" % section
        print section
        use = False
        res = []
        for line in lines:
            if not use and section in line:
                use = True
                continue
            elif use and section in line:
                use = False
                break
            if use:
                res.append(line)
        lines = res
        indent = len(lines[0]) - len(lines[0].lstrip())
        for i,line in enumerate(lines):
            lines[i] = line[indent:]
      
    text = replace_number_label(''.join(lines))
    text = re.sub(r"(?s)#<\?(.*?)>.+?#<\?/>", lambda mo:u"#<?>%s" % mo.group(1), text)
    #text = (u"#程序文件:%s\n" % filename) + text
    retnode = nodes.literal_block(text, text, source=fn)
    retnode.line = 1
    if self.options.get('language', ''):
        retnode['language'] = self.options['language']
    if 'linenos' in self.options:
        retnode['linenos'] = True
    document.settings.env.note_dependency(rel_fn)
    #print "LiteralInclude hacked"
    return [retnode]    

def setup(app):
    code.LiteralInclude.option_spec["section"] = directives.unchanged_required
    code.LiteralInclude.run = run