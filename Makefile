#!/usr/bin/make -f

mdwn_pages = $(shell find -name '*.mdwn')

html_pages = $(patsubst %.mdwn,%.html,$(mdwn_pages))

pdf_files = $(patsubst %.mdwn,%.pdf,$(mdwn_pages))

MDWN_TO_HTML = ./mdwn2html
HTML_TO_PDF  = wkhtmltopdf

all: $(html_pages) $(pdf_files)
	@echo "All done."

%.html: %.mdwn $(MDWN_TO_HTML)
	@echo "Transforming $< into $@"
	$(MDWN_TO_HTML) $< $@
#	title="$(shell head -1 $@.tmp|sed 's,</\?h1>,,g')" \
#		sed "s#@@title@@#$$title#" _head
#	title=`head -1 $@.tmp|sed 's,</\?h1>,,g'` \
#		sed "s#@@title@@#$title#" _head

%.pdf: %.html
	$(HTML_TO_PDF) $< $@

clean:
	@echo "Removing all generated html files"
	rm -f $(html_pages)


.PHONY: clean
