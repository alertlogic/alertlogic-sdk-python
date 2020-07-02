# Minimal makefile for Sphinx documentation
#

.PHONY: clean

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = python -msphinx
SPHINXPROJ    = alertlogic-sdk-python
SOURCEDIR     = .
BUILDDIR      = _build

APISDIR       = $(shell printf "import alsdkdefs\nprint(alsdkdefs.get_apis_dir())" | python)
APIDOCSDIR	  = ./$(BUILDDIR)/api_html
APISPECFILES  := $(shell find $(APISDIR) -name '*.yaml')
APIDOCFILES   := $(subst $(APISDIR),$(APIDOCSDIR),$(APISPECFILES:%.yaml=%.html))

VPATH 		  = $(APISDIR)

REDOC		  = npx redoc-cli
REDOCOPTS     = bundle -t _redoc_templates/page.html.hsb


# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

redoc: $(APIDOCFILES)

$(APIDOCSDIR)/%.html: %.yaml
	$(eval SERVICEBASE=$(shell sh -c "echo '$@' | sed -Ee 's/\/[a-zA-Z0-9_\-\.]+\.html//g'"))
	$(REDOC) $(REDOCOPTS) $< -o $@
	cp -r _redoc_templates/content '$(SERVICEBASE)/'


# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
html: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

clean:
	rm -fr $(APIDOCSDIR)
