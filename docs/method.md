# Method Note

## Experiment

This repository implements a fixed-layout GHZ witness experiment on IBM Quantum hardware. The state-preparation circuit is a nearest-neighbor GHZ chain:

1. Apply `H` to qubit `0`.
2. Apply a linear chain of `CX` gates from qubit `0` to qubit `N - 1`.
3. Measure one circuit in the computational basis.
4. Measure a family of phase-rotated circuits in the equatorial basis.

The hardware layout is not discovered at runtime. The experiment uses curated low-error chains on Heron-family devices so the transpiler can preserve a direct line embedding without routing.

## Witness Construction

The witness uses two observables:

- `P = P(0...0) + P(1...1)`, the population concentrated in the two GHZ endpoint states
- `A`, the fitted amplitude of the parity oscillation measured over evenly spaced equatorial phases

The lower bound reported by the repository is

`F_lb = (P + A) / 2`

For this GHZ witness, `F_lb > 0.5` is the certification threshold for genuine multipartite entanglement.

## Equatorial-Basis Scan

For each phase `phi`, the circuit applies `Rz(-phi)` followed by `H` on every qubit before measurement. The measured parity is

`Pi(phi) = sum_z (-1)^(wt(z)) p(z | phi)`

where `wt(z)` is the Hamming weight of bitstring `z`.

The parity data are fit to

`Pi(phi) = A * cos(N * phi + phi0)`

using a linear least-squares fit in the cosine and sine basis.

## Runtime Configuration

The hardware run uses `SamplerV2` with:

- dynamical decoupling enabled
- gate twirling enabled
- measurement twirling enabled

The transpilation is accepted only if it preserves the fixed layout without inserted `SWAP` gates and keeps the GHZ preparation to exactly `N - 1` two-qubit interactions.
