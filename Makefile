.PHONY: install demo

install:
	poetry install

demo:
	poetry run streamlit run demo_app.py

demo-eval:
	poetry run python3 demo_eval_sync.py

