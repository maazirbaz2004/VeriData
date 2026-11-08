.PHONY: setup test lint run-all run-one make-messy compare report

PYTHON ?= python

setup:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -e .

test:
	$(PYTHON) -m pytest --cov=src/ads --cov-report=term-missing

lint:
	$(PYTHON) -m ruff check src tests scripts

make-messy:
	$(PYTHON) -m ads.cli make-messy --seed 42

run-all:
	$(PYTHON) -m ads.cli run-all

run-one:
	$(PYTHON) -m ads.cli run --input $(INPUT) --name $(DATASET)

compare:
	$(PYTHON) -m ads.cli compare

report:
	$(PYTHON) -m ads.cli report

