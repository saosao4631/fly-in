MAIN := main.py

MAP  ?= maps/easy/01_linear_path.txt
ARGS ?=

UV := uv

MYPY_FLAGS := --warn-return-any --warn-unused-ignores \
              --ignore-missing-imports --disallow-untyped-defs \
              --check-untyped-defs

.PHONY: install run debug lint lint-strict test clean fclean re

install:
	$(UV) sync

run:
	$(UV) run python $(MAIN) $(MAP) $(ARGS)

debug:
	$(UV) run python -m pdb $(MAIN) $(MAP) $(ARGS)

lint:
	$(UV) run flake8 .
	$(UV) run mypy . $(MYPY_FLAGS)

lint-strict:
	$(UV) run flake8 .
	$(UV) run mypy . --strict

test:
	$(UV) run pytest -q

clean:
	rm -rf .mypy_cache .pytest_cache
	find . -type d -name '__pycache__' -not -path './.venv/*' \
	    -exec rm -rf {} +
	find . -type f -name '*.py[co]' -not -path './.venv/*' -delete

fclean: clean
	rm -rf .venv

re: fclean install
