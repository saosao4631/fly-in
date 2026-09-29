VENV   := .venv
MAIN   := main.py

MAP    ?= maps/easy_1.map
ARGS   ?=

PYTHON := python3
PIP    := $(VENV)/bin/pip
FLAKE8 := $(VENV)/bin/flake8
MYPY   := $(VENV)/bin/mypy
PYTEST := $(VENV)/bin/pytest

MYPY_FLAGS := --warn-return-any --warn-unused-ignores \
              --ignore-missing-imports --disallow-untyped-defs \
              --check-untyped-defs

.PHONY: help install run debug lint lint-strict test clean fclean re

install: $(VENV)

$(VENV): requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@touch $(VENV)

run:
	$(PYTHON) $(MAIN) $(MAP) $(ARGS)

debug:
	$(PYTHON) -m pdb $(MAIN) $(MAP) $(ARGS)

lint: $(VENV)
	$(FLAKE8) .
	$(MYPY) . $(MYPY_FLAGS)

lint-strict: $(VENV)
	$(FLAKE8) .
	$(MYPY) . --strict

test: $(VENV)
	$(PYTEST) -q

clean:
	rm -rf .mypy_cache .pytest_cache
	find . -type d -name '__pycache__' -not -path './$(VENV)/*' \
	    -exec rm -rf {} +
	find . -type f -name '*.py[co]' -not -path './$(VENV)/*' -delete

fclean: clean
	rm -rf $(VENV)

re: fclean install
