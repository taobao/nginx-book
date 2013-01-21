# -*- coding: utf-8 -*-
from docutils import nodes
import sphinx.writers.html as html
import pdb

def setup(app):
    old_visit_reference = html.HTMLTranslator.visit_reference
    def visit_reference(self, node):
        if node.get('refid','').startswith("fig-"):
            text = node.children[0].children[0].astext()
            node.children[0].children[0] = nodes.Text(u"【图:%s】" % text)
        old_visit_reference(self, node)
    html.HTMLTranslator.visit_reference = visit_reference