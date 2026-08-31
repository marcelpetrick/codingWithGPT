# Convenience targets -- everything works with plain python3 as well.
PY ?= python3

.PHONY: help crawl parse classify report serve open all clean-data

help:
	@echo "make crawl     download the schedule into data/raw/ (cached, use FORCE=1 to refetch)"
	@echo "make parse     data/raw/ -> data/congress.json + web/data.js (includes tagging)"
	@echo "make report    re-run the highlight rules and list what was tagged"
	@echo "make serve     serve web/ on http://localhost:8765"
	@echo "make open      open the viewer in the default browser (file://)"
	@echo "make all       crawl + parse"

crawl:
	$(PY) crawler/crawl.py $(if $(FORCE),--force,)

parse:
	$(PY) crawler/parse.py

classify report:
	$(PY) crawler/classify.py --report

serve:
	@echo "http://localhost:8765/index.html"
	$(PY) -m http.server 8765 --directory web

open:
	xdg-open web/index.html

all: crawl parse

# Deliberately not a default target: it throws away the local copy.
clean-data:
	rm -rf data/raw
