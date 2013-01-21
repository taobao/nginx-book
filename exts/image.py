# -*- coding: utf-8 -*-  
import os.path as path
import os
from docutils import nodes
from glob import glob
import imghdr
from sphinx.environment import BuildEnvironment
from docutils.utils import relative_path
from sphinx.builders.latex import LaTeXBuilder
from sphinx.builders.html import StandaloneHTMLBuilder
def process_images(self, docname, doctree):
    """
    Process and rewrite image URIs.
    """
    docdir = path.dirname(self.doc2path(docname, base=None))
    for node in doctree.traverse(nodes.image):
        # Map the mimetype to the corresponding image.  The writer may
        # choose the best image from these candidates.  The special key * is
        # set if there is only single candidate to be used by a writer.
        # The special key ? is set for nonlocal URIs.
        node['candidates'] = candidates = {}
        imguri = node['uri']
        if imguri.find('://') != -1:
            self.warn(docname, 'nonlocal image URI found: %s' % imguri,
                      node.line)
            candidates['?'] = imguri
            continue
        # imgpath is the image path *from srcdir*
        if imguri.startswith('/') or imguri.startswith(os.sep):
            # absolute path (= relative to srcdir)
            imgpath = path.normpath(imguri[1:])
        else:
            imgpath = path.normpath(path.join(docdir, imguri))
        # set imgpath as default URI
        node['uri'] = imgpath
        if imgpath.endswith(os.extsep + '*'):
            for filename in glob(path.join(self.srcdir, imgpath)):
                new_imgpath = relative_path(self.srcdir, filename)
                if filename.lower().endswith('.pdf'):
                    candidates['application/pdf'] = new_imgpath
                elif filename.lower().endswith('.svg'):
                    candidates['image/svg+xml'] = new_imgpath
                elif ".latex." in filename.lower():
                    candidates['latex'] = new_imgpath
                elif ".html." in filename.lower():
                    candidates['html'] = new_imgpath
                else:
                    try:
                        f = open(filename, 'rb')
                        try:
                            imgtype = imghdr.what(f)
                        finally:
                            f.close()
                    except (OSError, IOError), err:
                        self.warn(docname, 'image file %s not '
                                  'readable: %s' % (filename, err),
                                  node.line)
                    if imgtype:
                        candidates['image/' + imgtype] = new_imgpath
        else:
            candidates['*'] = imgpath
        # map image paths to unique image names (so that they can be put
        # into a single directory)
        for imgpath in candidates.itervalues():
            self.dependencies.setdefault(docname, set()).add(imgpath)
            if not os.access(path.join(self.srcdir, imgpath), os.R_OK):
                self.warn(docname, 'image file not readable: %s' % imgpath,
                          node.line)
                continue
            self.images.add_file(docname, imgpath)
 
from sphinx.util import url_re, get_matching_docs, docname_join, \
     FilenameUniqDict          

def add_file(self, docname, newfile):
    if newfile in self:
        self[newfile][0].add(docname)
        return self[newfile][1]
    uniquename = path.basename(newfile)
    self[newfile] = (set([docname]), uniquename)
    self._existing.add(uniquename)
    return uniquename

def setup(app):
    FilenameUniqDict.add_file = add_file
    BuildEnvironment.process_images = process_images
    LaTeXBuilder.supported_image_types.insert(0, "latex")
    StandaloneHTMLBuilder.supported_image_types.insert(0, "html")
