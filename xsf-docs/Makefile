#!/usr/bin/make -f

mdwn_pages = $(shell find -name '*.mdwn')

html_pages = $(patsubst %.mdwn,%.html,$(mdwn_pages))

pdf_files = $(patsubst %.mdwn,%.pdf,$(mdwn_pages))

txt_files = $(patsubst %.mdwn,%.txt,$(mdwn_pages))

MDWN_TO_HTML = ./mdwn2html
HTML_TO_PDF  = wkhtmltopdf
HTML_TO_TXT  = w3m -dump
CSS_FILE     = xsf.css
SVG_LOGO     = xsf.svg
PNG_LOGO     = xsf.png

all_files = $(html_pages) $(pdf_files) $(txt_files) $(CSS_FILE) $(SVG_LOGO) $(PNG_LOGO)

all: html pdf txt $(PNG_LOGO)

html: $(html_pages)

pdf: $(pdf_files)

txt: $(txt_files)

%.html: %.mdwn $(MDWN_TO_HTML)
	$(MDWN_TO_HTML) $< $@

%.pdf: %.html $(CSS_FILE) $(SVG_LOGO)
	$(HTML_TO_PDF) $< $@

# Plain markdown is actually more readable than html dumped to plain
# text (e.g. through w3m):
%.txt: %.mdwn
	cp $< $@

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
	rm -f $(html_pages) $(pdf_files) $(txt_files)


.PHONY: clean html pdf all
