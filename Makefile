.PHONY: dev test eval seed index-kb

PYTHON ?= .venv/bin/python

dev:
	$(PYTHON) -m uvicorn app.main:app --reload

test:
	$(PYTHON) -m pytest

eval:
	$(PYTHON) evals/run_evals.py

seed:
	$(PYTHON) scripts/seed_db.py

index-kb:
	$(PYTHON) scripts/index_kb.py

