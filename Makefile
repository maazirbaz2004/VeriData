.PHONY: setup test test-all lint run-all run-one make-messy compare report hypotheses eval-nl

PYTHON ?= python

setup:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -e .

test:
	$(PYTHON) -m pytest --cov=src/veridata --cov-report=term-missing -m "not slow"

test-all:
	$(PYTHON) -m pytest --cov=src/veridata --cov-report=term-missing

lint:
	$(PYTHON) -m ruff check src tests scripts

make-messy:
	$(PYTHON) -m veridata.cli make-messy --seed 42

run-all:
	$(PYTHON) -m veridata.cli run-all

run-one:
	$(PYTHON) -m veridata.cli run --input $(INPUT) --name $(DATASET)

hypotheses:
	$(PYTHON) -m veridata.cli hypotheses --dataset $(DATASET) --no-llm

eval-nl:
	$(PYTHON) scripts/eval_nl_parser.py

compare:
	$(PYTHON) -m veridata.cli compare

report:
	$(PYTHON) -m veridata.cli report

