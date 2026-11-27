.PHONY: setup test test-all lint run-all run-one make-messy compare report hypotheses eval-nl app eval-all-dev eval-all final-report

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

test-dataset:
	$(PYTHON) -m veridata.cli test --dataset $(DATASET)

eval-nl:
	$(PYTHON) scripts/eval_nl_parser.py

compare:
	$(PYTHON) -m veridata.cli compare

report:
	$(PYTHON) -m veridata.cli report

app:
	streamlit run src/veridata/app/main.py

eval-all-dev:
	$(PYTHON) -m veridata.cli eval run --experiment all --suite core60 --split dev

eval-all:
	$(PYTHON) -m veridata.cli eval run --experiment all --suite core60 --split test --confirm-final

final-report:
	$(PYTHON) -m veridata.cli eval tables --suite core60 --split dev
	$(PYTHON) -m veridata.cli eval figures --suite core60 --split dev
	$(PYTHON) -m veridata.cli final-report --suite core60 --split dev

