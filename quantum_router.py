"""Quantum route selection for the Connector God System.

Problem: given a set of connectors, pick the best 3-connector route cover --
the trio of connectors a task should flow through -- minimizing a total cost
built from gate cost, latency class, and fuel state, plus pairwise
synergy/friction terms between connectors.

Method: the subset-selection problem is encoded as a QUBO (with a quadratic
penalty enforcing |subset| == 3), converted to an Ising Hamiltonian, and
solved with QAOA (reps=3, COBYLA) executed on the Qiskit Aer simulator
(backend "aer_simulator"). An exact classical brute force over all
C(8, 3) = 56 subsets is computed alongside as ground truth.

HONEST LABELS:
- This runs a real quantum circuit on a CLASSICAL SIMULATOR. It is not a
  QPU run and no quantum speedup is claimed.
- All weights (gate costs, latency classes, fuel penalties, and the
  pairwise edge matrix) are DESIGN PARAMETERS chosen by the architects,
  informed by each connector's gate/fuel classification in
  connectors.json. They are not measured data and no benchmark is implied.

Author: Empire / Smoldering Abyss -- Kali Fleet: OMEGA quantum track.
"""

from __future__ import annotations

import itertools
import json
from dataclasses import dataclass

import numpy as np

# ---------------------------------------------------------------------------
# Connector table.
#
# gate / fuel mirror the classification in connectors.json (project root):
#   GitHub  -- gate: approval,        fuel: LIVE
#   Notion  -- gate: none,            fuel: LIVE
#   Stripe  -- gate: approval,        fuel: LIVE
#   Supabase-- gate: vault,           fuel: WIRED-NOT-FUELED
#   Nebius  -- gate: vault,           fuel: WIRED-NOT-FUELED (Token Factory)
#   Hermes  -- gate: boss-hands,      fuel: BLOCKED (PC agent)
#   Telegram-- gate: vault,           fuel: BLOCKED (crew bridge)
#   Gmail   -- gate: approval,        fuel: LIVE
# ---------------------------------------------------------------------------

CONNECTORS: list[str] = [
    "GitHub",
    "Notion",
    "Stripe",
    "Supabase",
    "Nebius",
    "Hermes",
    "Telegram",
    "Gmail",
]

_GATE = {
    "GitHub": "approval",
    "Notion": "none",
    "Stripe": "approval",
    "Supabase": "vault",
    "Nebius": "vault",
    "Hermes": "boss-hands",
    "Telegram": "vault",
    "Gmail": "approval",
}

_FUEL = {
    "GitHub": "LIVE",
    "Notion": "LIVE",
    "Stripe": "LIVE",
    "Supabase": "WIRED-NOT-FUELED",
    "Nebius": "WIRED-NOT-FUELED",
    "Hermes": "BLOCKED",
    "Telegram": "BLOCKED",
    "Gmail": "LIVE",
}

# --- DESIGN PARAMETERS (not measured data) ---------------------------------
# Cost-component scales. A connector's node cost is the sum of its three
# components: how hard its approval gate is, how penalized its fuel state
# is, and its latency class (live API < wired-but-unfueled < blocked).
GATE_COST = {"none": 0, "approval": 1, "vault": 2, "boss-hands": 3}
FUEL_COST = {"LIVE": 0, "WIRED-NOT-FUELED": 2, "BLOCKED": 4}
LATENCY_COST = {"LIVE": 0, "WIRED-NOT-FUELED": 1, "BLOCKED": 3}

# Pairwise edge weights (DESIGN PARAMETERS, not measured data): negative =
# synergy (the pair composes well in a route), positive = friction.
# Keyed by connector-name pair; symmetric; unspecified pairs default to 0.
EDGE_WEIGHTS: dict[tuple[str, str], int] = {
    ("GitHub", "Notion"): -1,     # docs live next to code
    ("GitHub", "Stripe"): 0,
    ("GitHub", "Supabase"): -1,   # repo webhooks -> data layer
    ("GitHub", "Nebius"): -2,     # CI -> inference deploy pipeline
    ("GitHub", "Hermes"): -1,     # agent operates repos
    ("GitHub", "Telegram"): 1,
    ("GitHub", "Gmail"): 1,
    ("Notion", "Stripe"): 0,
    ("Notion", "Supabase"): -1,   # notes mirror structured data
    ("Notion", "Nebius"): 0,
    ("Notion", "Hermes"): -1,     # agent reads/writes its own notes
    ("Notion", "Telegram"): 0,
    ("Notion", "Gmail"): -1,      # mail summaries land in notes
    ("Stripe", "Supabase"): -2,   # billing records -> database
    ("Stripe", "Nebius"): 1,
    ("Stripe", "Hermes"): 0,
    ("Stripe", "Telegram"): 1,    # payment alerts are noisy mid-route
    ("Stripe", "Gmail"): -1,      # receipts / invoice mail
    ("Supabase", "Nebius"): -1,   # stored data -> inference
    ("Supabase", "Hermes"): -1,   # agent state persistence
    ("Supabase", "Telegram"): 1,
    ("Supabase", "Gmail"): 0,
    ("Nebius", "Hermes"): -2,     # the agent runs on inference
    ("Nebius", "Telegram"): 1,
    ("Nebius", "Gmail"): 1,
    ("Hermes", "Telegram"): -2,   # the agent's control channel
    ("Hermes", "Gmail"): 0,
    ("Telegram", "Gmail"): 1,     # two human channels in one route = split
}

ROUTE_SIZE = 3
# Cardinality penalty weight (design parameter), sized from the cost table:
# the cheapest infeasible subsets (any cardinality != 3) have raw cost 0,
# tying the feasible optimum (also 0). Any A >= 1 breaks the tie in favor
# of feasible routes; A = 5 gives strict dominance (cheapest k=2 subset
# totals 5, cheapest k=4 totals 6) while keeping the route-cost signal
# strong relative to the penalty scale -- at A = 20 the penalty drowned
# the cost differences and QAOA could not resolve them (measured).
PENALTY_A = 5.0


def _edge(i: str, j: str) -> int:
    if (i, j) in EDGE_WEIGHTS:
        return EDGE_WEIGHTS[(i, j)]
    if (j, i) in EDGE_WEIGHTS:
        return EDGE_WEIGHTS[(j, i)]
    return 0


@dataclass(frozen=True)
class NodeInfo:
    name: str
    gate: str
    fuel: str
    gate_cost: int
    fuel_cost: int
    latency_cost: int

    @property
    def cost(self) -> int:
        return self.gate_cost + self.fuel_cost + self.latency_cost


def node_table() -> list[NodeInfo]:
    return [
        NodeInfo(
            name=n,
            gate=_GATE[n],
            fuel=_FUEL[n],
            gate_cost=GATE_COST[_GATE[n]],
            fuel_cost=FUEL_COST[_FUEL[n]],
            latency_cost=LATENCY_COST[_FUEL[n]],
        )
        for n in CONNECTORS
    ]


def subset_cost(subset: tuple[int, ...] | list[int]) -> float:
    """Exact classical cost of a candidate route (by connector index)."""
    table = node_table()
    names = [CONNECTORS[i] for i in subset]
    total = sum(table[i].cost for i in subset)
    for a, b in itertools.combinations(names, 2):
        total += _edge(a, b)
    return float(total)


def brute_force() -> list[dict]:
    """All C(8,3) subsets ranked by exact cost (ground truth)."""
    ranked = []
    for combo in itertools.combinations(range(len(CONNECTORS)), ROUTE_SIZE):
        ranked.append(
            {
                "indices": list(combo),
                "route": [CONNECTORS[i] for i in combo],
                "cost": subset_cost(combo),
            }
        )
    ranked.sort(key=lambda r: r["cost"])
    return ranked


# ---------------------------------------------------------------------------
# QUBO -> Ising.
# Minimize  sum_i c_i x_i + sum_{i<j} q_ij x_i x_j + A (sum_i x_i - k)^2
# Penalty expansion (x_i^2 = x_i):
#   A (sum x)^2 - 2Ak sum x + A k^2
#   = A [ sum_i x_i + 2 sum_{i<j} x_i x_j ] - 2Ak sum_i x_i + A k^2
# Effective coefficients:  c'_i = c_i + A(1 - 2k),  q'_ij = q_ij + 2A,
# constant A k^2.  With x_i = (1 - Z_i)/2 this becomes an Ising operator.
# ---------------------------------------------------------------------------

def build_ising_terms():
    """Return (h, J, offset): Ising coefficients of the penalized QUBO.

    Energy of a basis state = sum_i h_i Z_i + sum_{i<j} J_ij Z_i Z_j + offset,
    which equals the QUBO objective (route cost + cardinality penalty).
    """
    n = len(CONNECTORS)
    table = node_table()
    lin = np.zeros(n)
    quad = np.zeros((n, n))
    for i in range(n):
        lin[i] = table[i].cost + PENALTY_A * (1 - 2 * ROUTE_SIZE)
    for i, j in itertools.combinations(range(n), 2):
        quad[i, j] = _edge(CONNECTORS[i], CONNECTORS[j]) + 2 * PENALTY_A
    const = PENALTY_A * ROUTE_SIZE**2

    # Ising coefficients after x = (1 - Z)/2:
    #   h_i (Z_i)      = -lin_i/2 - sum_{j != i} quad_ij / 4
    #   J_ij (Z_i Z_j) = quad_ij / 4
    #   offset         = sum lin_i / 2 + sum_{i<j} quad_ij / 4 + const
    h = np.zeros(n)
    offset = const + sum(lin) / 2.0
    J: dict[tuple[int, int], float] = {}
    for i, j in itertools.combinations(range(n), 2):
        offset += quad[i, j] / 4.0
        h[i] -= quad[i, j] / 4.0
        h[j] -= quad[i, j] / 4.0
        J[(i, j)] = quad[i, j] / 4.0
    for i in range(n):
        h[i] -= lin[i] / 2.0
    return h, J, float(offset)


def build_cost_operator():
    from qiskit.quantum_info import SparsePauliOp

    n = len(CONNECTORS)
    h, J, _offset = build_ising_terms()

    terms: list[tuple[str, complex]] = []
    for i in range(n):
        if abs(h[i]) > 1e-12:
            label = ["I"] * n
            label[n - 1 - i] = "Z"  # rightmost char = qubit 0
            terms.append(("".join(label), h[i]))
    for (i, j), coeff in J.items():
        if abs(coeff) > 1e-12:
            label = ["I"] * n
            label[n - 1 - i] = "Z"
            label[n - 1 - j] = "Z"
            terms.append(("".join(label), coeff))
    op = SparsePauliOp.from_list(terms)
    _h, _J, offset = build_ising_terms()
    return op, float(offset)


def build_qaoa_circuit(reps: int):
    """Parameterized QAOA circuit built from native gates.

    U(beta, gamma) = prod_p [ exp(-i beta_p sum_i X_i) . exp(-i gamma_p H_C) ]
    applied to |+>^n, with H_C the Ising cost Hamiltonian (offset excluded --
    a constant phase). Built gate-by-gate (CNOT/RZ/RX) rather than via
    Pauli-evolution synthesis: identical unitary, far cheaper to bind and
    simulate. Parameters are ordered [gamma_0..gamma_{p-1}, beta_0..beta_{p-1}].
    """
    from qiskit import QuantumCircuit
    from qiskit.circuit import Parameter

    n = len(CONNECTORS)
    h, J, _offset = build_ising_terms()
    # Normalize coefficients by the penalty scale so the variational angles
    # live at O(1) scale (QAOA is scale-covariant; see solve_qaoa).
    scale = PENALTY_A
    h = h / scale
    J = {k: v / scale for k, v in J.items()}
    gammas = [Parameter(f"g{p}") for p in range(reps)]
    betas = [Parameter(f"b{p}") for p in range(reps)]
    qc = QuantumCircuit(n)
    qc.h(range(n))
    for p in range(reps):
        g = gammas[p]
        for i in range(n):
            if abs(h[i]) > 1e-12:
                qc.rz(2.0 * g * float(h[i]), i)
        for (i, j), coeff in J.items():
            if abs(coeff) > 1e-12:
                qc.cx(i, j)
                qc.rz(2.0 * g * float(coeff), j)
                qc.cx(i, j)
        for i in range(n):
            qc.rx(2.0 * betas[p], i)
    return qc, gammas + betas


def _decode(bitstring: str) -> list[int]:
    """Aer counts key -> chosen connector indices (rightmost char = qubit 0)."""
    n = len(CONNECTORS)
    return [i for i in range(n) if bitstring[n - 1 - i] == "1"]


def solve_qaoa(shots: int = 8192, reps: int = 3, seed: int = 1234) -> dict:
    """Run QAOA on the Qiskit Aer simulator; return route + measurements."""
    from scipy.optimize import minimize
    from qiskit import transpile
    from qiskit.quantum_info import SparsePauliOp, Statevector
    from qiskit_aer import AerSimulator

    # The cardinality penalty (A=20) puts the raw Hamiltonian on an energy
    # scale of ~hundreds, where useful QAOA gammas are tiny and a naive
    # optimizer stalls. QAOA is scale-covariant, so optimize the NORMALIZED
    # operator H/S (S = PENALTY_A) and scale the expectation back.
    scale = PENALTY_A
    h, J, offset = build_ising_terms()
    n = len(CONNECTORS)
    norm_terms: list[tuple[str, complex]] = []
    for i in range(n):
        label = ["I"] * n
        label[n - 1 - i] = "Z"
        norm_terms.append(("".join(label), h[i] / scale))
    for (i, j), coeff in J.items():
        label = ["I"] * n
        label[n - 1 - i] = "Z"
        label[n - 1 - j] = "Z"
        norm_terms.append(("".join(label), coeff / scale))
    norm_op = SparsePauliOp.from_list(norm_terms)

    ansatz, parameters = build_qaoa_circuit(reps)

    def expectation(params: np.ndarray) -> float:
        bound = ansatz.assign_parameters(dict(zip(parameters, params)))
        ev = Statevector(bound).expectation_value(norm_op)
        return float(ev.real * scale + offset)

    # Multi-start COBYLA: one heuristic start + seeded random starts,
    # then a low-rhobeg polish pass from the best point found.
    rng = np.random.default_rng(seed)
    starts = [
        np.concatenate(
            [np.linspace(0.2, 0.6, reps), np.linspace(np.pi / 4, np.pi / 8, reps)]
        )
    ]
    for _ in range(5):
        starts.append(
            np.concatenate(
                [rng.uniform(0.0, 1.0, reps), rng.uniform(0.0, np.pi, reps)]
            )
        )
    opt = None
    for x0 in starts:
        res = minimize(
            expectation,
            x0,
            method="COBYLA",
            options={"maxiter": 250, "rhobeg": 0.2},
        )
        if opt is None or res.fun < opt.fun:
            opt = res
    polish = minimize(
        expectation,
        opt.x,
        method="COBYLA",
        options={"maxiter": 200, "rhobeg": 0.05},
    )
    if polish.fun < opt.fun:
        opt = polish

    backend = AerSimulator(seed_simulator=seed)
    circuit = ansatz.assign_parameters(dict(zip(parameters, opt.x)))
    circuit.measure_all()
    counts = (
        backend.run(transpile(circuit, backend), shots=shots)
        .result()
        .get_counts()
    )

    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    counts_top10 = [
        {
            "bitstring": bs,
            "count": int(c),
            "route": [CONNECTORS[i] for i in _decode(bs)],
            "feasible": len(_decode(bs)) == ROUTE_SIZE,
            "cost": subset_cost(_decode(bs)) if len(_decode(bs)) == ROUTE_SIZE else None,
        }
        for bs, c in top[:10]
    ]
    # Chosen route: most-sampled feasible (size-3) bitstring.
    chosen_entry = next(e for e in counts_top10 if e["feasible"]) \
        if any(e["feasible"] for e in counts_top10) else None
    if chosen_entry is None:  # widen the search beyond top-10 if needed
        for bs, _c in top:
            idx = _decode(bs)
            if len(idx) == ROUTE_SIZE:
                chosen_entry = {
                    "bitstring": bs,
                    "route": [CONNECTORS[i] for i in idx],
                    "cost": subset_cost(idx),
                }
                break

    return {
        "backend": backend.name,
        "backend_is_simulator": True,
        "shots": shots,
        "reps": reps,
        "seed": seed,
        "penalty_A": PENALTY_A,
        "optimal_expectation": float(opt.fun),
        "optimal_parameters": [float(p) for p in opt.x],
        "counts_top10": counts_top10,
        "chosen_route": chosen_entry["route"],
        "chosen_bitstring": chosen_entry["bitstring"],
        "chosen_route_cost": chosen_entry["cost"],
    }


def main() -> dict:
    ranked = brute_force()
    result = solve_qaoa()
    result["brute_force_optimum"] = ranked[0]
    result["brute_force_top5"] = ranked[:5]
    result["subsets_evaluated_classically"] = len(ranked)
    chosen_cost = result["chosen_route_cost"]
    result["chosen_route_rank"] = (
        sum(1 for r in ranked if r["cost"] < chosen_cost) + 1
    )
    result["chosen_route_is_optimal"] = chosen_cost == ranked[0]["cost"]
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
