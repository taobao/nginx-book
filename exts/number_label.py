# -*- coding: utf-8 -*-
from docutils import nodes
import sphinx.writers.latex as latex
import sphinx.writers.html as html

CircleNumbers = u"❶❷❸❹❺❻❼❽❾❿"

def replace_latex_code_labels(t):
    for i, n in enumerate(CircleNumbers):
        target = r"{\normalsize\ding{%s}}" % (202+i)
        target2 = r"[@normalsize@ding[%s]]" % (202+i)
        t = t.replace(r"\PYG{c}{\PYGZsh{}%s}" % n, target)
        t = t.replace(r"\PYG{c}{\#%s}" % n, target)
        t = t.replace(r"@#%s" % n, target2)
    return t
    
def replace_latex_text_labels(t):
    for i, n in enumerate(CircleNumbers):
        t = t.replace(n, r"{\Large\ding{%s}}\hspace{1mm}" % (202+i))
    return t
    
def replace_html_code_labels(t):
    for i, n in enumerate(CircleNumbers):
        target = '<span class="prebc">#</span><span class="codenumber">%s</span>' % n
        t = t.replace("#%s" % n, target).replace("#{%d}" % (i+1), target).replace("#{{%d}}" % (i+1), "#{%d}" % (i+1))
    return t
    
def setup(app):
    print "number_label loaded"
    old_depart_literal_block = latex.LaTeXTranslator.depart_literal_block
    def depart_literal_block(self, node):
        old_depart_literal_block(self, node)
        self.body[-1] = replace_latex_code_labels(self.body[-1])
    latex.LaTeXTranslator.depart_literal_block = depart_literal_block
    latex.LaTeXTranslator.depart_doctest_block = depart_literal_block
    
    old_visit_Text = latex.LaTeXTranslator.visit_Text
    def visit_Text(self, node):
        old_visit_Text(self, node)
        self.body[-1] = replace_latex_text_labels(self.body[-1])
    latex.LaTeXTranslator.visit_Text = visit_Text
    
    old_visit_literal_block = html.HTMLTranslator.visit_literal_block
    def visit_literal_block(self, node):
        try:
            old_visit_literal_block(self, node)
        finally:
            self.body[-1] = replace_html_code_labels(self.body[-1])
            
    html.HTMLTranslator.visit_literal_block = visit_literal_block
    html.HTMLTranslator.visit_doctest_block = visit_literal_block