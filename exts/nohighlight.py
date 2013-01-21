from sphinx import highlighting
def highlight_block(self, source, lang, linenos=False, warn=None):
    return self.unhighlighted(source)
highlighting.PygmentsBridge.highlight_block = highlight_block