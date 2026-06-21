.PHONY: dev test eval eval-live seed index-kb

PYTHON ?= .venv/bin/python

dev:
	$(PYTHON) -m uvicorn app.main:app --reload

test:
	$(PYTHON) -m pytest

eval:
	$(PYTHON) evals/run_evals.py

eval-live:
	@if [ -z "$$OPENAI_API_KEY" ]; then \
		echo "Skipping live OpenAI evals: OPENAI_API_KEY is not set."; \
	else \
		AGENT_RUNTIME=openai $(PYTHON) evals/run_evals.py --runtime openai; \
	fi

seed:
	$(PYTHON) scripts/seed_db.py

index-kb:
	$(PYTHON) scripts/index_kb.py
