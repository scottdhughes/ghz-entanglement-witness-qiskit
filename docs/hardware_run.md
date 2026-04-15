# Hardware Run Note

## Backend

- Backend: `ibm_marrakesh`
- Job ID: `d7fnkn56agrc738itqfg`
- Instance: `open-instance`
- Physical qubit chain: `31, 18, 11, 12, 13, 14, 15, 19, 35, 34, 33, 39`

## Transpilation

- Logical qubits: `12`
- Logical depth: `12`
- Transpiled depth: `48`
- Transpiled two-qubit depth: `11`
- Transpiled two-qubit gate count: `11`

The transpilation was accepted only if it preserved the fixed layout without inserted SWAP gates and kept the GHZ preparation at exactly `11` two-qubit gates.

## Witness Data

- `P0 = 0.3251`
- `P1 = 0.3092`
- `P = 0.6343`
- `A = 0.4836`
- `F_lb = 0.5590`
- `gme_witness_pass = True`

## Parity Scan

| Phase (rad) | Parity |
| ---: | ---: |
| 0.000 | 0.5703 |
| 0.483 | 0.4863 |
| 0.967 | 0.3594 |
| 1.450 | 0.1787 |
| 1.933 | -0.0059 |
| 2.417 | -0.1914 |
| 2.900 | -0.4170 |
| 3.383 | -0.4619 |
| 3.867 | -0.3867 |
| 4.350 | -0.2207 |
| 4.833 | -0.0879 |
| 5.317 | 0.1895 |
| 5.800 | 0.3994 |


## Additional Hardware Runs

| Qubits | Backend | Job ID | Z shots | Phase shots | `P` | `A` | `F_lb` | Witness pass |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `16` | `ibm_kingston` | `d7fhlpe2cugc739qj4j0` | `4096` | `1024` | `0.5459` | `0.3730` | `0.4594` | `False` |
| `16` | `ibm_fez` | `d7fncb21u7fs739m7i7g` | `8192` | `2048` | `0.3607` | `0.2278` | `0.2943` | `False` |
| `20` | `ibm_kingston` | `d7fhkmtd4lnc73ffc030` | `4096` | `1024` | `0.4172` | `0.2858` | `0.3515` | `False` |

