#!/usr/bin/make -f

txt_files = $(shell find -name '*.txt' -a ! -name '.*.txt')

html_files = $(patsubst %.txt,%.html,$(txt_files))

pdf_files = $(patsubst %.txt,%.pdf,$(txt_files))

TXT_TO_HTML  = asciidoc
HTML_TO_PDF  = wkhtmltopdf
CSS_FILE     = xsf.css
SVG_LOGO     = xsf.svg
PNG_LOGO     = xsf.png

all_files = $(html_files) $(pdf_files) $(txt_files) $(CSS_FILE) $(SVG_LOGO) $(PNG_LOGO)

all: html pdf $(PNG_LOGO)

html: $(html_files)

pdf: $(pdf_files)

%.html: %.txt
	$(TXT_TO_HTML) $<

%.pdf: %.html $(CSS_FILE) $(SVG_LOGO)
	$(HTML_TO_PDF) $< $@

# We usually don't need to run this one, but it's easier to keep both
# SVN and PNG logos in sync:
$(PNG_LOGO): $(SVG_LOGO)
	inkscape $< -e $@

install: $(all_files)
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
