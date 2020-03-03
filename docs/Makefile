# Minimal makefile for Sphinx documentation
#

.PHONY: clean

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = python -msphinx
SPHINXPROJ    = alertlogic-sdk-python
SOURCEDIR     = .
BUILDDIR      = _build

APISDIR       = ../almdrlib/apis
APIDOCSDIR	  = ./$(BUILDDIR)/api_html
APISPECFILES  := $(shell find $(APISDIR) -name '*.yaml')
APIDOCFILES   := $(subst $(APISDIR),$(APIDOCSDIR),$(APISPECFILES:%.yaml=%.html))

REDOC		  = npx redoc-cli
REDOCOPTS     = bundle

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

redoc: $(APIDOCFILES)

$(APIDOCSDIR)/%.html: $(APISPECFILES)
	@echo $@
	@echo $<
	$(REDOC) $(REDOCOPTS) $< -o $@


# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
html: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

clean:
	rm -fr $(APIDOCSDIR)
