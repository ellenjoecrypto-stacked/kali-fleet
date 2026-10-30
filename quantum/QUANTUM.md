# Quantum Track — Connector God System Route Selection

**Label: SIMULATOR.** Everything below is a real QAOA quantum circuit executed
on a **classical simulator** (Qiskit Aer, backend `aer_simulator`). It is not a
QPU run, and no quantum speedup is claimed or implied. The full machine record
is in `results.json` next to this file.

## What ran

- **Module:** `../quantum_router.py` — route selection for the Connector God
  System posed as an optimization problem: choose the best 3-connector route
  cover from 8 connectors (GitHub, Notion, Stripe, Supabase, Nebius, Hermes,
  Telegram, Gmail).
- **Formulation:** node costs from each connector's gate class, fuel state,
  and latency class (as classified in `../connectors.json`); pairwise
  synergy/friction edge weights; cardinality |route| = 3 enforced by a
  quadratic penalty (A = 5, sized from the cost table — see module comments).
  Encoded QUBO → Ising, verified coefficient-exact against the classical
  objective on all 256 basis states.
- **Algorithm:** QAOA, reps = 3, native-gate ansatz (H + RZ/CNOT cost layers +
  RX mixer layers), multi-start COBYLA (6 starts + polish) over exact
  statevector expectations, final sampling on Aer.
- **Stack (pinned at install):** qiskit 2.6.1 · qiskit-aer 0.18.2 ·
  qiskit-algorithms 0.4.0 (installed this session; rustworkx 0.18.1,
  stevedore 5.9.1 as dependencies), project venv `~/workspace/venv`.
- **Recorded run:** 2026-10-30 11:33:52 → 11:34:27 UTC (06:33 CDT),
  35.5 s wall, 8192 shots, seed 1234.

## Result (real output, from `results.json`)

- **QAOA chosen route: Notion + Stripe + Gmail — cost 0.0.**
- **That is the exact brute-force optimum** (rank 1 of all 56 subsets,
  verified classically; next-best subsets cost 1.0).
- The optimum bitstring `10000110` was the single most-sampled outcome
  (214 / 8192 shots). Optimized expectation ⟨H⟩ = 10.255 (the distribution
  still spreads — QAOA at reps = 3 concentrates on the optimum without
  collapsing onto it; the modal feasible sample is the readout).
- Brute-force top 5: {Notion, Stripe, Gmail} 0.0 · {GitHub, Notion, Stripe}
  1.0 · {GitHub, Notion, Gmail} 1.0 · {GitHub, Notion, Supabase} 3.0 ·
  {GitHub, Notion, Nebius} 3.0.
- **Tests:** `../test_quantum_router.py` — 3 tests, all pass (35.3 s):
  universe size/ranking, node-cost sanity vs the registry classification,
  and QAOA-on-Aer returning a route in the brute-force top 5 (the recorded
  full runs did better — the optimum; the test guarantees the top-5 bound).

## Honesty ledger

- **Weights are design parameters, not measured data.** The gate/fuel/latency
  cost scales and the entire pairwise edge matrix are architectural choices
  written explicitly in `quantum_router.py`, informed by the connectors'
  gate/fuel classification — not by benchmarks or telemetry. The "best
  route" is best *under those stated parameters*.
- Simulator ≠ QPU: Aer's statevector evolution is exact classical linear
  algebra. Sampling noise here is algorithmic (finite shots over an exact
  state), not hardware noise.

## QPU rung — PENDING-TOKEN

- Presence check this session: `QISKIT_IBM_RUNTIME_API_TOKEN` — **UNSET**;
  `IBM_QUANTUM_TOKEN` — **UNSET**. No token exists on this machine, so no QPU
  submission was attempted.
- **Exact remaining step:** create an IBM Quantum account under
  **jadaru.exe@gmail.com** → generate an API token in the IBM Quantum
  dashboard → deposit the token through the **Secure Vault** (never through
  chat or code). With the token present as `QISKIT_IBM_RUNTIME_API_TOKEN`,
  the same circuit and cost operator can be submitted to a real IBM backend
  via Qiskit Runtime.
- **What a QPU run would change:** the circuit, formulation, and readout stay
  identical. What changes is the execution substrate — real device noise
  (gate/readout error, decoherence), queue time, and finite-shot statistics
  over a noisy state instead of an exact one — so the modal feasible sample
  may need more shots and error mitigation (e.g., readout mitigation, ZNE)
  to resolve the same optimum. At 8 qubits the problem is far below any
  quantum-advantage regime; the QPU rung is a portability/honesty proof,
  not a performance claim.
