# -*- coding: utf-8 -*-
from sphinx.util.compat import Directive
import shutil
import pdb
import os.path as path
from docutils.parsers.rst import directives
from docutils import nodes

def build_finished(app, ex):
    if app.builder.name == "latex":
        import glob
        curpath = path.split(__file__)[0]
        for fn in glob.glob(path.join(curpath, "latexstyle", "*.*")):
            print "copy %s" % fn
            shutil.copy(fn, path.join(app.builder.outdir, path.split(fn)[-1]))

class timgblock(nodes.Part, nodes.Element):
    pass

def latex_visit_timgblock(self, node):
    text = r"""
\framebox[1.0 \textwidth]{
\includegraphics[width=2.5em]{%(image)s.pdf}
\raisebox{1.0em}{\parbox{0.9 \textwidth}{\small
    """
    self.body.append( text % node)
    self.context.append("}}}")

def latex_depart_timgblock(self, node):
    self.body.append(self.context.pop())

def html_visit_timgblock(self, node):
    text = r"""<div class="imagebox" style="background-image: url(_static/%(image)s.png)">"""
    self.body.append(text % node)
    self.context.append("</div>")
    
def html_depart_timgblock(self, node):
    self.body.append(self.context.pop())

def empty_visit(self, node):
    raise nodes.SkipNode
    
class ImageBlockDirective(Directive):
    has_content = True
    required_arguments = 0
    optional_arguments = 2
    final_argument_whitespace = True
    option_spec = {
        'text': directives.unchanged
    }
    image = ""

    def run(self):
        node = timgblock()
        node["image"] = self.image
        if self.arguments and self.arguments[0]:
            node['argument'] = u" ".join(self.arguments)        
        self.state.nested_parse(self.content, self.content_offset, node)
        ret = [node]
        return ret    
    
def MakeFileDirective(imgname):
    #curpath = path.split(__file__)[0]
    #shutil.copy(path.join(curpath, imgname + ".pdf"), path.join(curpath, "..\\..\\build\\latex"))
    return type(imgname+"Directive",(ImageBlockDirective,),{"image":imgname})

def setup(app):
    #pdb.set_trace()
    app.add_node(timgblock, 
        latex=(latex_visit_timgblock, latex_depart_timgblock),
        text=(empty_visit, None), 
        html=(html_visit_timgblock, html_depart_timgblock))
    app.add_directive('tcode', MakeFileDirective("code"))
    app.add_directive('tanim', MakeFileDirective("anim"))
    app.add_directive('twarning', MakeFileDirective("warning"))
    app.add_directive('tlink', MakeFileDirective("link"))
    app.add_directive('ttip', MakeFileDirective("tip"))
    app.add_directive('tthink', MakeFileDirective("think"))
    app.connect("build-finished", build_finished)