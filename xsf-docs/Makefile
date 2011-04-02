#!/usr/bin/make -f

txt_files = $(shell find -name '*.txt' -a ! -name '.*.txt')

html_files = $(patsubst %.txt,%.html,$(txt_files))

pdf_files = $(patsubst %.txt,%.pdf,$(txt_files))

TXT_TO_HTML  = asciidoc -a linkcss
HTML_TO_PDF  = wkhtmltopdf
CSS_FILE     = xsf.css
ADOC_CSS_FILE= asciidoc-xhtml11.css
ADOC_JS_FILE = asciidoc-xhtml11.js
SVG_LOGO     = xsf.svg
PNG_LOGO     = xsf.png

all_files = $(html_files) $(txt_files) $(CSS_FILE) $(ADOC_CSS_FILE) $(ADOC_JS_FILE) $(SVG_LOGO) $(PNG_LOGO)

all: html $(PNG_LOGO)

html: $(html_files)

pdf: $(pdf_files)

%.html: rel_path=$(shell echo $@|sed 's,[^/],,g;s,/,../,g')
%.html: link_home=$(shell echo "<a href=\"$(rel_path)index.html\">XSF</a> / ")
%.html: %.txt
	@echo " HTML $@"
	@$(TXT_TO_HTML) -o $@.tmp $<
	@echo " HOME $@"
	@if [ $< != index.txt ]; then sed -i 's,<h1>,<h1>$(link_home),' $@.tmp; fi
	@echo " CSS  $@"
	@sed -i 's,\(rel="stylesheet" href="\)[^"]*,\1$(rel_path)$(CSS_FILE),' $@.tmp
	@echo " JS   $@"
	@sed -i 's,\(type="text/javascript" src="\)[^"]*,\1$(rel_path)$(ADOC_JS_FILE),' $@.tmp
	@mv $@.tmp $@

%.pdf: %.html $(CSS_FILE) $(ADOC_CSS_FILE) $(ADOC_JS_FILE) $(SVG_LOGO)
	@echo " GEN  $@"
	@$(HTML_TO_PDF) $< $@

# We usually don't need to run this one, but it's easier to keep both
# SVN and PNG logos in sync:
$(PNG_LOGO): $(SVG_LOGO)
	inkscape $< -e $@

install:
	@if [ -z "$(DESTDIR)" ]; then \
		echo 'E: DESTDIR is not set, not installing.'; exit 1; \
	fi
	mkdir -p $(DESTDIR)
	# There are probably better ways:
	set -e; for i in $(all_files); do \
		d=$(DESTDIR)/`dirname $$i` && \
		mkdir -p $$d && \
		install $$i $$d; \
	done

clean:
	@echo "Removing all generated files"
	rm -f $(html_files) $(pdf_files)


.PHONY: clean html pdf all
