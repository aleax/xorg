#!/usr/bin/make -f

mdwn_pages = $(shell find -name '*.mdwn')

html_pages = $(patsubst %.mdwn,%.html,$(mdwn_pages))

pdf_files = $(patsubst %.mdwn,%.pdf,$(mdwn_pages))

MDWN_TO_HTML = ./mdwn2html
HTML_TO_PDF  = wkhtmltopdf
CSS_FILE     = xsf.css
SVG_LOGO     = xsf.svg
PNG_LOGO     = xsf.png

all: html pdf $(PNG_LOGO)

html: $(html_pages)

pdf: $(pdf_files)

%.html: %.mdwn $(MDWN_TO_HTML)
	$(MDWN_TO_HTML) $< $@

%.pdf: %.html $(CSS_FILE) $(SVG_LOGO)
	$(HTML_TO_PDF) $< $@

# We usually don't need to run this one, but it's easier to keep both
# SVN and PNG logos in sync:
$(PNG_LOGO): $(SVG_LOGO)
	inkscape $< -e $@

clean:
	@echo "Removing all generated html files"
	rm -f $(html_pages) $(pdf_files)


.PHONY: clean html pdf all
