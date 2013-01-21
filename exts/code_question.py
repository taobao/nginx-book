# -*- coding: utf-8 -*-
from docutils import nodes
import sphinx.writers.latex as latex
import sphinx.writers.html as html

def replace_latex_question_mark(t):
    return t.replace(r"\PYGZsh{}\textless{}?\textgreater{}", u"\\large{【你的程序】}")
       
def replace_html_question_mark(t):
    return t.replace("#&lt;?&gt;", u'<span style="font-size:16px;font-weight:bold;">【你的程序】</span>')
    
def setup(app):
    print "code question loaded"
    old_depart_literal_block = latex.LaTeXTranslator.depart_literal_block
    def depart_literal_block(self, node):
        old_depart_literal_block(self, node)
        self.body[-1] = replace_latex_question_mark(self.body[-1])
    latex.LaTeXTranslator.depart_literal_block = depart_literal_block
    latex.LaTeXTranslator.depart_doctest_block = depart_literal_block
       
    old_visit_literal_block = html.HTMLTranslator.visit_literal_block
    def visit_literal_block(self, node):
        try:
            old_visit_literal_block(self, node)
        finally:
            self.body[-1] = replace_html_question_mark(self.body[-1])
            
    html.HTMLTranslator.visit_literal_block = visit_literal_block
    html.HTMLTranslator.visit_doctest_block = visit_literal_block