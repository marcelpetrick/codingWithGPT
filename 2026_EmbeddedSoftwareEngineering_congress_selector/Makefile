# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>

# Thin wrapper around run.py -- on Windows just call `py run.py` directly.
PY ?= python3

.PHONY: help run serve refresh report crawl parse clean

help:
	@echo "make run       bootstrap everything and open the viewer (this is the one)"
	@echo "make serve     same, but on http://localhost:8765 instead of file://"
	@echo "make refresh   re-download the schedule, then rebuild and open"
	@echo "make report    re-run the highlight rules and list what was tagged"
	@echo "make clean     remove .venv and every downloaded or generated file"
	@echo
	@echo "low level (need requests + beautifulsoup4 in \$$PY):"
	@echo "make crawl     download into data/raw/     make parse   build the viewer data"

run:
	$(PY) run.py

serve:
	$(PY) run.py --serve

refresh:
	$(PY) run.py --refresh

report:
	$(PY) crawler/classify.py --report

crawl:
	$(PY) crawler/crawl.py

parse:
	$(PY) crawler/parse.py

clean:
	$(PY) run.py --clean
