PYTHON ?= python3

.PHONY: venv install local hardware render

venv:
	$(PYTHON) -m venv .venv

install:
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

local:
	. .venv/bin/activate && python ghz_witness.py --mode local --qubits 12 --phase-points 13

hardware:
	. .venv/bin/activate && python ghz_witness.py --mode hardware --backend ibm_marrakesh --qubits 12 --phase-points 13

render:
	. .venv/bin/activate && python scripts/render_docs.py --result results/ghz12_witness_marrakesh_phase13.json --comparison-results results/ghz16_witness_result.json,results/ghz16_witness_ibm_fez.json,results/ghz20_witness_result.json --circuit-image assets/ghz12_marrakesh_phase13_circuit.png --histogram-image assets/ghz12_marrakesh_phase13_population_histogram.png --parity-image assets/ghz12_marrakesh_phase13_parity_fit.png
