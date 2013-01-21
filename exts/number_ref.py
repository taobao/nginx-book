# -*- coding: utf-8 -*-
from docutils import nodes
import sphinx.writers.latex as latex
from sphinx.util.nodes import clean_astext
import pdb
def doctree_resolved(app, doctree, docname):
    """将带sec-开头的target标签名添加到标签的父节点之上
    这样就可以在section节点之下定义章节的标签。便于用
    leo的auto-rst功能编辑rst文档。
    
    例如：
    
    章节名称
    --------
    
    .. _sec-test:

    章节内容
    """
    for node in doctree.traverse(nodes.target):
        if node.get("refid", "").startswith("sec-"):
            section = node.parent
            section["ids"].append(node["refid"])
            node["refid"] = "-" + node["refid"]

def doctree_read(app, doctree):
    """
    为了sec-开头标签能正常工作需要将其添加进：
    env.domains["std"].data["labels"]
    sec-test: 文章名, 标签名, 章节名，
    """
    labels = app.env.domains["std"].data["labels"]
    for name, _ in doctree.nametypes.iteritems():
        if not name.startswith("sec-"): continue
        labelid = doctree.nameids[name]
        node = doctree.ids[labelid].parent
        if node.tagname == 'section':
            sectname = clean_astext(node[0])
            labels[name] = app.env.docname, labelid, sectname
            
def setup(app):
    print "number_ref loaded"
    old_visit_reference = latex.LaTeXTranslator.visit_reference
    def visit_reference(self, node):
        uri = node.get('refuri', '')
        hashindex = uri.find('#')
        if hashindex == -1:
            id = uri[1:] + '::doc'
        else:
            id = uri[1:].replace('#', ':')
        if uri.startswith("%") and "#fig-" in uri:
            self.body.append(self.hyperlink(id))
            self.body.append(u"图\\ref*{%s}" % id)
            self.context.append("}}")
            raise nodes.SkipChildren
        elif uri.startswith("%") and "#sec-" in uri:
            self.body.append(self.hyperlink(id))
            self.body.append(u"第\\ref*{%s}节" % id)
            self.context.append("}}")
            raise nodes.SkipChildren        
        else:
            return old_visit_reference(self, node)
    latex.LaTeXTranslator.visit_reference = visit_reference
    
    app.connect("doctree-read", doctree_read)
    app.connect("doctree-resolved", doctree_resolved)