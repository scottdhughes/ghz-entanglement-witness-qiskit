#!/usr/bin/env python3
"""Run a GHZ multipartite-entanglement witness on IBM Quantum hardware."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.visualization import plot_histogram
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit_ibm_runtime.options import SamplerOptions


PRIMARY_BACKEND = "ibm_kingston"
FALLBACK_BACKEND = "ibm_fez"
BACKEND_CHAINS: dict[str, list[int]] = {
    "ibm_kingston": [
        69,
        78,
        89,
        90,
        91,
        92,
        93,
        79,
        73,
        74,
        75,
        59,
        55,
        54,
        53,
        52,
        51,
        50,
        49,
        38,
    ],
    "ibm_fez": [
        93,
        92,
        91,
        90,
        89,
        88,
        87,
        97,
        107,
        106,
        105,
        117,
        125,
        124,
        123,
        136,
        143,
        142,
        141,
        140,
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a GHZ multipartite-entanglement witness experiment."
    )
    parser.add_argument(
        "--mode",
        choices=("hardware", "local"),
        default="hardware",
        help="Execution target. Hardware uses IBM Runtime; local uses AerSimulator.",
    )
    parser.add_argument(
        "--instance",
        default="open-instance",
        help="IBM Quantum Runtime instance name for hardware mode.",
    )
    parser.add_argument(
        "--backend",
        default="auto",
        help="Backend name to use. 'auto' prefers ibm_kingston, then ibm_fez.",
    )
    parser.add_argument(
        "--job-id",
        default=None,
        help="Existing IBM Runtime job ID to analyze instead of submitting a new hardware run.",
    )
    parser.add_argument(
        "--qubits",
        type=int,
        default=20,
        help="Number of logical qubits in the GHZ witness circuit.",
    )
    parser.add_argument(
        "--shots-z",
        type=int,
        default=4096,
        help="Shots for the Z-basis population circuit.",
    )
    parser.add_argument(
        "--shots-phase",
        type=int,
        default=1024,
        help="Shots for each equatorial-basis parity circuit.",
    )
    parser.add_argument(
        "--phase-points",
        type=int,
        default=12,
        help="Number of evenly spaced equatorial phases to sample.",
    )
    parser.add_argument(
        "--optimization-level",
        type=int,
        default=1,
        choices=(0, 1, 2, 3),
        help="Preset transpiler optimization level for hardware mode.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=7,
        help="Seed for reproducible local sampling and transpilation.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Where to write the summary JSON. Defaults depend on execution mode.",
    )
    parser.add_argument(
        "--save-circuit",
        default="assets/ghz20_circuit.png",
        help="Where to save the logical GHZ circuit diagram.",
    )
    parser.add_argument(
        "--save-parity",
        default="assets/ghz20_parity_fit.png",
        help="Where to save the parity-oscillation plot.",
    )
    parser.add_argument(
        "--save-histogram",
        default="assets/ghz20_population_histogram.png",
        help="Where to save the Z-basis population histogram.",
    )
    return parser.parse_args()


def validate_requested_qubits(backend_name: str | None, qubits: int) -> None:
    if qubits <= 1:
        raise ValueError("At least 2 qubits are required for a GHZ witness.")
    if backend_name and backend_name in BACKEND_CHAINS and qubits > len(BACKEND_CHAINS[backend_name]):
        raise ValueError(
            f"{backend_name} only has a curated chain of length {len(BACKEND_CHAINS[backend_name])}."
        )
    if backend_name is None and qubits > len(BACKEND_CHAINS[PRIMARY_BACKEND]):
        raise ValueError("The curated hardware layouts support up to 20 qubits.")


def build_ghz_core(num_qubits: int) -> QuantumCircuit:
    circuit = QuantumCircuit(num_qubits, name=f"ghz_{num_qubits}")
    circuit.h(0)
    for qubit in range(num_qubits - 1):
        circuit.cx(qubit, qubit + 1)
    return circuit


def build_population_circuit(num_qubits: int) -> QuantumCircuit:
    circuit = QuantumCircuit(num_qubits, num_qubits, name=f"ghz_{num_qubits}_z")
    circuit.compose(build_ghz_core(num_qubits), inplace=True)
    circuit.barrier()
    circuit.measure(range(num_qubits), range(num_qubits))
    return circuit


def build_phase_circuit(num_qubits: int, phase: float) -> QuantumCircuit:
    circuit = QuantumCircuit(num_qubits, num_qubits, name=f"ghz_{num_qubits}_phase")
    circuit.compose(build_ghz_core(num_qubits), inplace=True)
    circuit.barrier()
    for qubit in range(num_qubits):
        circuit.rz(-phase, qubit)
        circuit.h(qubit)
    circuit.measure(range(num_qubits), range(num_qubits))
    circuit.metadata = {"phase": phase}
    return circuit


def build_phase_grid(phase_points: int) -> list[float]:
    return [math.tau * index / phase_points for index in range(phase_points)]


def save_circuit_figure(circuit: QuantumCircuit, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure = circuit.draw("mpl", fold=30, idle_wires=False, style="iqp")
    figure.savefig(path, bbox_inches="tight")
    figure.clf()


def save_histogram_figure(counts: dict[str, int], output_path: str, limit: int = 12) -> None:
    top_counts = dict(sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit])
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure = plot_histogram(top_counts, figsize=(12, 4.8), color="#53d1b6")
    figure.savefig(path, bbox_inches="tight")
    figure.clf()


def save_parity_figure(
    phases: list[float],
    parities: list[float],
    amplitude: float,
    phase_offset: float,
    num_qubits: int,
    output_path: str,
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    phase_array = np.array(phases, dtype=float)
    parity_array = np.array(parities, dtype=float)
    fit_x = np.linspace(0.0, math.tau, 720)
    fit_y = amplitude * np.cos(num_qubits * fit_x + phase_offset)

    figure, axis = plt.subplots(figsize=(10.5, 4.8))
    axis.plot(fit_x, fit_y, color="#53d1b6", linewidth=2.2, label="fit")
    axis.scatter(phase_array, parity_array, color="#0f172a", s=48, zorder=3, label="measured")
    axis.set_xlabel("Equatorial phase $\\phi$")
    axis.set_ylabel("Parity")
    axis.set_title(f"{num_qubits}-Qubit GHZ Parity Oscillation")
    axis.set_xlim(0.0, math.tau)
    axis.set_ylim(-1.05, 1.05)
    axis.grid(alpha=0.18)
    axis.legend(frameon=False)
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def physical_chain_for_backend(backend_name: str, qubits: int) -> list[int]:
    if backend_name not in BACKEND_CHAINS:
        raise ValueError(
            f"Unsupported backend '{backend_name}'. Supported layouts: {', '.join(BACKEND_CHAINS)}."
        )
    chain = BACKEND_CHAINS[backend_name]
    if qubits > len(chain):
        raise ValueError(f"Requested {qubits} qubits, but curated chain has only {len(chain)}.")
    return chain[:qubits]


def resolve_backend(service: QiskitRuntimeService, backend_name: str) -> str:
    if backend_name != "auto":
        return backend_name

    for candidate in (PRIMARY_BACKEND, FALLBACK_BACKEND):
        backend = service.backend(candidate)
        if backend.status().operational:
            return candidate
    raise RuntimeError(
        f"Neither {PRIMARY_BACKEND} nor {FALLBACK_BACKEND} is operational for instance 'open-instance'."
    )


def count_two_qubit_gates(circuit: QuantumCircuit) -> int:
    return sum(
        1
        for instruction in circuit.data
        if instruction.operation.num_qubits == 2 and not instruction.operation.name.startswith("measure")
    )


def transpile_for_backend(
    circuits: list[QuantumCircuit],
    *,
    backend: Any,
    physical_chain: list[int],
    optimization_level: int,
    seed: int,
) -> list[QuantumCircuit]:
    pass_manager = generate_preset_pass_manager(
        optimization_level=optimization_level,
        backend=backend,
        initial_layout=physical_chain,
        routing_method="none",
        seed_transpiler=seed,
    )
    transpiled_circuits = [pass_manager.run(circuit) for circuit in circuits]

    z_circuit = transpiled_circuits[0]
    swap_count = int(z_circuit.count_ops().get("swap", 0))
    two_qubit_count = count_two_qubit_gates(z_circuit)
    expected_two_qubit_count = len(physical_chain) - 1
    if swap_count != 0:
        raise RuntimeError("Rejected transpilation because routing inserted SWAP gates.")
    if two_qubit_count != expected_two_qubit_count:
        raise RuntimeError(
            f"Rejected transpilation because it used {two_qubit_count} two-qubit gates "
            f"instead of the expected {expected_two_qubit_count}."
        )
    return transpiled_circuits


def extract_counts(data_bin: Any) -> dict[str, int]:
    if hasattr(data_bin, "keys"):
        for key in data_bin.keys():
            value = data_bin[key]
            if hasattr(value, "get_counts"):
                counts = value.get_counts()
                return {bitstring: int(count) for bitstring, count in counts.items()}

    for name in dir(data_bin):
        if name.startswith("_"):
            continue
        value = getattr(data_bin, name)
        if hasattr(value, "get_counts"):
            counts = value.get_counts()
            return {bitstring: int(count) for bitstring, count in counts.items()}

    raise KeyError("No count-bearing classical register found in runtime result data.")


def parity_from_counts(counts: dict[str, int]) -> float:
    total = sum(counts.values())
    parity = 0.0
    for bitstring, count in counts.items():
        ones = bitstring.count("1")
        parity += ((-1) ** ones) * count
    return parity / total


def fit_parity_curve(phases: list[float], parities: list[float], num_qubits: int) -> tuple[float, float]:
    phase_array = np.array(phases, dtype=float)
    parity_array = np.array(parities, dtype=float)
    design = np.column_stack(
        [
            np.cos(num_qubits * phase_array),
            np.sin(num_qubits * phase_array),
        ]
    )
    coefficients, _, _, _ = np.linalg.lstsq(design, parity_array, rcond=None)
    alpha, beta = coefficients
    amplitude = float(np.hypot(alpha, beta))
    phase_offset = float(math.atan2(-beta, alpha))
    return amplitude, phase_offset


def dominant_outcomes(counts: dict[str, int], limit: int = 12) -> list[dict[str, Any]]:
    total = sum(counts.values())
    rows = []
    for bitstring, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit]:
        rows.append(
            {
                "bitstring": bitstring,
                "count": int(count),
                "probability": count / total,
            }
        )
    return rows


def base_result(args: argparse.Namespace, logical_circuit: QuantumCircuit) -> dict[str, Any]:
    command = "python ghz_witness.py " + " ".join(sys.argv[1:])
    return {
        "experiment": "ghz_multipartite_entanglement_witness",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "instance": args.instance if args.mode == "hardware" else None,
        "requested_backend": args.backend,
        "qubit_count": args.qubits,
        "phase_points": args.phase_points,
        "shots_z": args.shots_z,
        "shots_phase": args.shots_phase,
        "logical_depth": logical_circuit.depth(),
        "logical_two_qubit_gate_count": count_two_qubit_gates(logical_circuit),
        "logical_operation_counts": {
            name: int(count) for name, count in logical_circuit.count_ops().items()
        },
        "command": command,
    }


def analyze_measurements(
    *,
    args: argparse.Namespace,
    backend_name: str,
    physical_qubits: list[int] | None,
    logical_circuit: QuantumCircuit,
    z_counts: dict[str, int],
    phase_counts: list[dict[str, int]],
    transpiled_reference: QuantumCircuit | None,
    job_id: str | None,
) -> dict[str, Any]:
    zero_state = "0" * args.qubits
    one_state = "1" * args.qubits
    total_z_shots = sum(z_counts.values())
    p0 = z_counts.get(zero_state, 0) / total_z_shots
    p1 = z_counts.get(one_state, 0) / total_z_shots
    population_sum = p0 + p1

    phases = build_phase_grid(args.phase_points)
    parities = [parity_from_counts(counts) for counts in phase_counts]
    amplitude, phase_offset = fit_parity_curve(phases, parities, args.qubits)
    fidelity_lower_bound = 0.5 * (population_sum + amplitude)

    result = base_result(args, logical_circuit)
    result.update(
        {
            "backend": backend_name,
            "job_id": job_id,
            "physical_qubits": physical_qubits,
            "phase_angles_radians": phases,
            "z_basis_counts": z_counts,
            "dominant_z_outcomes": dominant_outcomes(z_counts),
            "population_zero": p0,
            "population_one": p1,
            "population_sum": population_sum,
            "phase_scan": [
                {
                    "phase_radians": phase,
                    "parity": parity,
                    "counts": counts,
                }
                for phase, parity, counts in zip(phases, parities, phase_counts, strict=True)
            ],
            "parity_amplitude": amplitude,
            "phase_offset_radians": phase_offset,
            "fidelity_lower_bound": fidelity_lower_bound,
            "gme_witness_pass": fidelity_lower_bound > 0.5,
            "transpiled_depth": transpiled_reference.depth() if transpiled_reference else None,
            "transpiled_two_qubit_gate_count": (
                count_two_qubit_gates(transpiled_reference) if transpiled_reference else None
            ),
            "transpiled_two_qubit_depth": (
                transpiled_reference.depth(
                    lambda instruction_context: instruction_context.operation.num_qubits == 2
                )
                if transpiled_reference
                else None
            ),
            "transpiled_operation_counts": (
                {
                    name: int(count)
                    for name, count in transpiled_reference.count_ops().items()
                }
                if transpiled_reference
                else None
            ),
            "resilience": (
                {
                    "dynamical_decoupling": True,
                    "gate_twirling": True,
                    "measurement_twirling": True,
                }
                if args.mode == "hardware"
                else None
            ),
        }
    )
    return result


def run_local_experiment(args: argparse.Namespace) -> tuple[QuantumCircuit, dict[str, Any]]:
    logical_circuit = build_ghz_core(args.qubits)
    z_circuit = build_population_circuit(args.qubits)
    phases = build_phase_grid(args.phase_points)
    phase_circuits = [build_phase_circuit(args.qubits, phase) for phase in phases]

    simulator = AerSimulator(seed_simulator=args.seed)
    compiled_z = transpile(z_circuit, simulator, seed_transpiler=args.seed)
    z_counts = dict(Counter(simulator.run(compiled_z, shots=args.shots_z).result().get_counts()))

    compiled_phase = transpile(phase_circuits, simulator, seed_transpiler=args.seed)
    phase_counts = []
    for circuit in compiled_phase:
        counts = simulator.run(circuit, shots=args.shots_phase).result().get_counts()
        phase_counts.append(dict(Counter(counts)))

    result = analyze_measurements(
        args=args,
        backend_name="aer_simulator",
        physical_qubits=None,
        logical_circuit=logical_circuit,
        z_counts=z_counts,
        phase_counts=phase_counts,
        transpiled_reference=compiled_z,
        job_id=None,
    )
    result["seed"] = args.seed
    return logical_circuit, result


def run_hardware_experiment(args: argparse.Namespace) -> tuple[QuantumCircuit, dict[str, Any]]:
    service = QiskitRuntimeService(instance=args.instance)
    if args.job_id:
        job = service.job(args.job_id)
        job_backend_name = job.backend().name
        if args.backend != "auto" and args.backend != job_backend_name:
            raise ValueError(
                f"Requested backend '{args.backend}' does not match job backend '{job_backend_name}'."
            )
        backend_name = job_backend_name
    else:
        job = None
        backend_name = resolve_backend(service, args.backend)
    physical_qubits = physical_chain_for_backend(backend_name, args.qubits)
    backend = service.backend(backend_name)

    logical_circuit = build_ghz_core(args.qubits)
    z_circuit = build_population_circuit(args.qubits)
    phases = build_phase_grid(args.phase_points)
    phase_circuits = [build_phase_circuit(args.qubits, phase) for phase in phases]
    transpiled_circuits = transpile_for_backend(
        [z_circuit, *phase_circuits],
        backend=backend,
        physical_chain=physical_qubits,
        optimization_level=args.optimization_level,
        seed=args.seed,
    )

    if job is None:
        sampler_options = SamplerOptions()
        sampler_options.dynamical_decoupling.enable = True
        sampler_options.twirling.enable_gates = True
        sampler_options.twirling.enable_measure = True

        sampler = Sampler(mode=backend, options=sampler_options)
        pubs = [(transpiled_circuits[0], None, args.shots_z)] + [
            (circuit, None, args.shots_phase) for circuit in transpiled_circuits[1:]
        ]
        job = sampler.run(pubs)
    pub_results = job.result()

    z_counts = extract_counts(pub_results[0].data)
    phase_counts = [extract_counts(result.data) for result in pub_results[1:]]

    result = analyze_measurements(
        args=args,
        backend_name=backend_name,
        physical_qubits=physical_qubits,
        logical_circuit=logical_circuit,
        z_counts=z_counts,
        phase_counts=phase_counts,
        transpiled_reference=transpiled_circuits[0],
        job_id=job.job_id(),
    )
    return logical_circuit, result


def write_json(output_path: Path, payload: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    validate_requested_qubits(None if args.backend == "auto" else args.backend, args.qubits)

    logical_circuit, result = (
        run_local_experiment(args)
        if args.mode == "local"
        else run_hardware_experiment(args)
    )

    save_circuit_figure(logical_circuit, args.save_circuit)
    save_histogram_figure(result["z_basis_counts"], args.save_histogram)
    save_parity_figure(
        result["phase_angles_radians"],
        [row["parity"] for row in result["phase_scan"]],
        result["parity_amplitude"],
        result["phase_offset_radians"],
        result["qubit_count"],
        args.save_parity,
    )

    output_path = Path(
        args.output
        or (
            "results/ghz20_witness_local.json"
            if args.mode == "local"
            else "results/ghz20_witness_result.json"
        )
    )
    write_json(output_path, result)

    print(f"Mode: {result['mode']}")
    print(f"Backend: {result['backend']}")
    print(f"Job ID: {result['job_id']}")
    print(f"Population sum: {result['population_sum']:.6f}")
    print(f"Parity amplitude: {result['parity_amplitude']:.6f}")
    print(f"Fidelity lower bound: {result['fidelity_lower_bound']:.6f}")
    print(f"GME witness pass: {result['gme_witness_pass']}")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
