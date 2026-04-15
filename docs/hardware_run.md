# Hardware Run Note

## Backend

- Backend: `ibm_kingston`
- Job ID: `d7fhlpe2cugc739qj4j0`
- Instance: `open-instance`
- Physical qubit chain: `69, 78, 89, 90, 91, 92, 93, 79, 73, 74, 75, 59, 55, 54, 53, 52`

## Transpilation

- Logical qubits: `16`
- Logical depth: `16`
- Transpiled depth: `64`
- Transpiled two-qubit depth: `15`
- Transpiled two-qubit gate count: `15`

The transpilation was accepted only if it preserved the fixed layout without inserted SWAP gates and kept the GHZ preparation at exactly `15` two-qubit gates.

## Witness Data

- `P0 = 0.2720`
- `P1 = 0.2739`
- `P = 0.5459`
- `A = 0.3730`
- `F_lb = 0.4594`
- `gme_witness_pass = False`

## Parity Scan

| Phase (rad) | Parity |
| ---: | ---: |
| 0.000 | 0.3750 |
| 0.524 | -0.2852 |
| 1.047 | -0.1641 |
| 1.571 | 0.3379 |
| 2.094 | -0.2246 |
| 2.618 | -0.1152 |
| 3.142 | 0.3906 |
| 3.665 | -0.2324 |
| 4.189 | -0.0469 |
| 4.712 | 0.3691 |
| 5.236 | -0.2656 |
| 5.760 | -0.0684 |


## Comparison Run

- Comparison qubits: `20`
- Comparison backend: `ibm_kingston`
- Comparison job ID: `d7fhkmtd4lnc73ffc030`
- Comparison `F_lb`: `0.3515`
- Comparison witness pass: `False`

