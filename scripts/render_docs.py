#!/usr/bin/env python3
"""Render README, hardware notes, and a preview card from the result JSON."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render repo docs from a GHZ witness result JSON.")
    parser.add_argument(
        "--result",
        default="results/ghz20_witness_result.json",
        help="Path to the result JSON to use as the source of truth.",
    )
    parser.add_argument(
        "--readme",
        default="README.md",
        help="Where to write the repository README.",
    )
    parser.add_argument(
        "--hardware-doc",
        default="docs/hardware_run.md",
        help="Where to write the hardware-run note.",
    )
    parser.add_argument(
        "--preview",
        default="assets/repo_preview.png",
        help="Where to save the preview card image.",
    )
    parser.add_argument(
        "--circuit-image",
        default="assets/ghz20_circuit.png",
        help="Path to the circuit image referenced by the README.",
    )
    parser.add_argument(
        "--histogram-image",
        default="assets/ghz20_population_histogram.png",
        help="Path to the histogram image referenced by the README.",
    )
    parser.add_argument(
        "--parity-image",
        default="assets/ghz20_parity_fit.png",
        help="Path to the parity image referenced by the README.",
    )
    parser.add_argument(
        "--comparison-result",
        default=None,
        help="Optional second result JSON to summarize as a comparison run.",
    )
    return parser.parse_args()


def load_result(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def witness_statement(result: dict) -> str:
    qubits = result["qubit_count"]
    fidelity = result["fidelity_lower_bound"]
    if result["gme_witness_pass"]:
        return (
            f"The measured lower bound $F_{{lb}} = {fidelity:.3f}$ exceeds the multipartite "
            f"entanglement threshold of $0.5$, so this run certifies genuine {qubits}-partite "
            "entanglement for the GHZ witness used here."
        )
    return (
        f"The measured lower bound $F_{{lb}} = {fidelity:.3f}$ does not cross the $0.5$ witness "
        "threshold, so this repository presents the run as a hardware GHZ characterization result "
        "without the stronger certification claim."
    )


def format_probability(value: float) -> str:
    return f"{value:.4f}"


def render_readme(
    result: dict,
    *,
    circuit_image: str,
    histogram_image: str,
    parity_image: str,
    preview_image: str,
    result_json: str,
    comparison_result: dict | None,
) -> str:
    dominant_rows = "\n".join(
        f"| `{row['bitstring']}` | {row['count']} | {row['probability']:.4f} |"
        for row in result["dominant_z_outcomes"][:8]
    )
    physical_qubits = ", ".join(str(qubit) for qubit in result["physical_qubits"])
    phases = ", ".join(f"{phase:.3f}" for phase in result["phase_angles_radians"])
    circuit_name = Path(circuit_image).name
    histogram_name = Path(histogram_image).name
    parity_name = Path(parity_image).name
    preview_name = Path(preview_image).name
    result_name = Path(result_json).name
    comparison_block = ""
    if comparison_result:
        comparison_block = f"""
## Stretch Attempt

The repository also includes a higher-qubit stretch run on `{comparison_result['qubit_count']}` qubits from the same fixed-layout workflow:

| Field | Value |
| --- | --- |
| Backend | `{comparison_result['backend']}` |
| Job ID | `{comparison_result['job_id']}` |
| `P` | `{comparison_result['population_sum']:.4f}` |
| `A` | `{comparison_result['parity_amplitude']:.4f}` |
| `F_lb` | `{comparison_result['fidelity_lower_bound']:.4f}` |
| Witness pass | `{comparison_result['gme_witness_pass']}` |

That comparison captures the tradeoff directly: the same witness becomes harder to keep above threshold as the GHZ chain gets longer on current hardware.
"""
    return f"""# GHZ-{result['qubit_count']} Entanglement Witness on IBM Quantum Hardware

![GHZ witness preview](assets/{preview_name})

This repository packages a real IBM Quantum hardware run of a fixed-layout GHZ witness experiment on `{result['qubit_count']}` qubits. The workflow prepares a line-topology GHZ state, measures the GHZ populations in the computational basis, scans the equatorial-basis parity oscillation, and combines those observables into the lower-bound witness

`F_lb = (P + A) / 2`

where `P` is the GHZ population sum and `A` is the fitted parity amplitude.

{witness_statement(result)}

## Current Hardware Result

| Field | Value |
| --- | --- |
| Backend | `{result['backend']}` |
| Job ID | `{result['job_id']}` |
| Qubits | `{result['qubit_count']}` |
| Physical chain | `{physical_qubits}` |
| `P(0...0)` | `{format_probability(result['population_zero'])}` |
| `P(1...1)` | `{format_probability(result['population_one'])}` |
| `P = P0 + P1` | `{format_probability(result['population_sum'])}` |
| Parity amplitude `A` | `{result['parity_amplitude']:.4f}` |
| Lower bound `F_lb` | `{result['fidelity_lower_bound']:.4f}` |
| GME witness pass | `{result['gme_witness_pass']}` |
| Transpiled depth | `{result['transpiled_depth']}` |
| Two-qubit gate count | `{result['transpiled_two_qubit_gate_count']}` |

## Why This Witness Matters

The GHZ witness captures two distinct ingredients of a multipartite entangled state on real hardware:

- population concentrated in the `|0...0>` and `|1...1>` basis states
- coherent phase information that survives as a large parity oscillation in the equatorial basis

Taken together, these two observables separate a coherent GHZ state from a classical mixture of the same endpoint populations.

![Logical GHZ circuit](assets/{circuit_name})
![Population histogram](assets/{histogram_name})
![Parity fit](assets/{parity_name})

## Dominant Computational-Basis Outcomes

| Bitstring | Count | Probability |
| --- | ---: | ---: |
{dominant_rows}

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python ghz_witness.py --mode local --qubits {result['qubit_count']}
```

Run on IBM Quantum hardware:

```bash
python ghz_witness.py --mode hardware --backend auto --qubits {result['qubit_count']}
```

Regenerate the repo docs after a new run:

```bash
python scripts/render_docs.py --result results/{result_name}
```

## Measurement Configuration

- Z-basis shots: `{result['shots_z']}`
- Phase-circuit shots: `{result['shots_phase']}`
- Equatorial phases: `{phases}`
- Runtime resilience: dynamical decoupling, gate twirling, measurement twirling

{comparison_block}

## Repository Layout

```text
.
├── README.md
├── LICENSE
├── Makefile
├── ghz_witness.py
├── requirements.txt
├── assets/
│   ├── {circuit_name}
│   ├── {parity_name}
│   ├── {histogram_name}
│   └── {preview_name}
├── docs/
│   ├── hardware_run.md
│   └── method.md
├── results/
│   ├── ghz20_witness_local.json
│   └── {result_name}
└── scripts/
    └── render_docs.py
```

## Further Reading

- [Method note](docs/method.md)
- [Hardware run note](docs/hardware_run.md)
"""


def render_hardware_doc(result: dict, comparison_result: dict | None) -> str:
    scan_rows = "\n".join(
        f"| {row['phase_radians']:.3f} | {row['parity']:.4f} |"
        for row in result["phase_scan"]
    )
    chain = ", ".join(str(qubit) for qubit in result["physical_qubits"])
    comparison_block = ""
    if comparison_result:
        comparison_block = f"""

## Comparison Run

- Comparison qubits: `{comparison_result['qubit_count']}`
- Comparison backend: `{comparison_result['backend']}`
- Comparison job ID: `{comparison_result['job_id']}`
- Comparison `F_lb`: `{comparison_result['fidelity_lower_bound']:.4f}`
- Comparison witness pass: `{comparison_result['gme_witness_pass']}`
"""
    return f"""# Hardware Run Note

## Backend

- Backend: `{result['backend']}`
- Job ID: `{result['job_id']}`
- Instance: `{result['instance']}`
- Physical qubit chain: `{chain}`

## Transpilation

- Logical qubits: `{result['qubit_count']}`
- Logical depth: `{result['logical_depth']}`
- Transpiled depth: `{result['transpiled_depth']}`
- Transpiled two-qubit depth: `{result['transpiled_two_qubit_depth']}`
- Transpiled two-qubit gate count: `{result['transpiled_two_qubit_gate_count']}`

The transpilation was accepted only if it preserved the fixed layout without inserted SWAP gates and kept the GHZ preparation at exactly `{result['qubit_count'] - 1}` two-qubit gates.

## Witness Data

- `P0 = {result['population_zero']:.4f}`
- `P1 = {result['population_one']:.4f}`
- `P = {result['population_sum']:.4f}`
- `A = {result['parity_amplitude']:.4f}`
- `F_lb = {result['fidelity_lower_bound']:.4f}`
- `gme_witness_pass = {result['gme_witness_pass']}`

## Parity Scan

| Phase (rad) | Parity |
| ---: | ---: |
{scan_rows}
{comparison_block}
"""


def save_preview_card(result: dict, output_path: Path) -> None:
    phases = np.array(result["phase_angles_radians"], dtype=float)
    parities = np.array([row["parity"] for row in result["phase_scan"]], dtype=float)
    fit_x = np.linspace(0.0, math.tau, 720)
    fit_y = result["parity_amplitude"] * np.cos(
        result["qubit_count"] * fit_x + result["phase_offset_radians"]
    )

    top_rows = result["dominant_z_outcomes"][:8]
    labels = [row["bitstring"] for row in top_rows]
    values = [row["probability"] for row in top_rows]

    figure = plt.figure(figsize=(13.5, 7.2), facecolor="#0f172a")
    grid = figure.add_gridspec(2, 3, height_ratios=[1.0, 1.15], width_ratios=[1.2, 1.2, 1.0])

    title_axis = figure.add_subplot(grid[0, :2])
    title_axis.axis("off")
    title_axis.text(
        0.0,
        0.82,
        f"GHZ-{result['qubit_count']} Witness on {result['backend']}",
        color="white",
        fontsize=24,
        fontweight="bold",
    )
    title_axis.text(
        0.0,
        0.46,
        f"F_lb = {result['fidelity_lower_bound']:.3f}    P = {result['population_sum']:.3f}    "
        f"A = {result['parity_amplitude']:.3f}",
        color="#53d1b6",
        fontsize=16,
    )
    title_axis.text(
        0.0,
        0.16,
        witness_statement(result).replace("$", ""),
        color="#dbe4f0",
        fontsize=12,
        wrap=True,
    )

    meta_axis = figure.add_subplot(grid[0, 2])
    meta_axis.axis("off")
    meta_axis.text(
        0.0,
        0.86,
        f"Backend\n{result['backend']}\n\nJob ID\n{result['job_id']}\n\nQubits\n{result['qubit_count']}",
        color="white",
        fontsize=13,
        va="top",
    )

    parity_axis = figure.add_subplot(grid[1, :2])
    parity_axis.set_facecolor("#111827")
    parity_axis.plot(fit_x, fit_y, color="#53d1b6", linewidth=2.2)
    parity_axis.scatter(phases, parities, color="white", s=38, zorder=3)
    parity_axis.set_title("Parity Oscillation", color="white", fontsize=15)
    parity_axis.set_xlabel("Phase", color="#cbd5e1")
    parity_axis.set_ylabel("Parity", color="#cbd5e1")
    parity_axis.set_xlim(0.0, math.tau)
    parity_axis.set_ylim(-1.05, 1.05)
    parity_axis.tick_params(colors="#cbd5e1")
    for spine in parity_axis.spines.values():
        spine.set_color("#334155")
    parity_axis.grid(alpha=0.15)

    hist_axis = figure.add_subplot(grid[1, 2])
    hist_axis.set_facecolor("#111827")
    hist_axis.bar(range(len(labels)), values, color="#60a5fa")
    hist_axis.set_title("Top Z-Basis Outcomes", color="white", fontsize=15)
    hist_axis.set_ylabel("Probability", color="#cbd5e1")
    hist_axis.set_xticks(range(len(labels)))
    hist_axis.set_xticklabels(labels, rotation=90, fontsize=8, color="#cbd5e1")
    hist_axis.tick_params(colors="#cbd5e1")
    for spine in hist_axis.spines.values():
        spine.set_color("#334155")

    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=160, bbox_inches="tight", facecolor=figure.get_facecolor())
    plt.close(figure)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    args = parse_args()
    result = load_result(Path(args.result))
    comparison_result = load_result(Path(args.comparison_result)) if args.comparison_result else None
    write_text(
        Path(args.readme),
        render_readme(
            result,
            circuit_image=args.circuit_image,
            histogram_image=args.histogram_image,
            parity_image=args.parity_image,
            preview_image=args.preview,
            result_json=args.result,
            comparison_result=comparison_result,
        ),
    )
    write_text(Path(args.hardware_doc), render_hardware_doc(result, comparison_result))
    save_preview_card(result, Path(args.preview))
    print(f"Rendered {args.readme}")
    print(f"Rendered {args.hardware_doc}")
    print(f"Rendered {args.preview}")


if __name__ == "__main__":
    main()
