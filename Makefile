PYTHON ?= python3

.PHONY: venv install local hardware render

venv:
	$(PYTHON) -m venv .venv

install:
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

local:
	. .venv/bin/activate && python ghz_witness.py --mode local --qubits 16

hardware:
	. .venv/bin/activate && python ghz_witness.py --mode hardware --backend auto --qubits 16

render:
	. .venv/bin/activate && python scripts/render_docs.py --result results/ghz16_witness_result.json --backend-comparison-result results/ghz16_witness_ibm_fez.json --stretch-result results/ghz20_witness_result.json
