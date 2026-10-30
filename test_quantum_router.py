"""Tests for quantum_router: QAOA-on-Aer route selection vs brute force.

Claim under test (stated precisely): the QAOA solver, executed on the
Qiskit Aer SIMULATOR, returns a feasible 3-connector route whose exact
classical cost ranks in the TOP 5 of all 56 candidate subsets (rank =
count of subsets with strictly lower cost, + 1). Equality with the
brute-force optimum is reported by the module but is NOT asserted here;
the top-5 bound is what this test guarantees.

Run:  ~/workspace/venv/bin/python -m pytest test_quantum_router.py -v
(or plain unittest: ~/workspace/venv/bin/python -m unittest test_quantum_router)
"""

import unittest

import quantum_router as qr


class TestBruteForce(unittest.TestCase):
    def test_universe_size(self):
        ranked = qr.brute_force()
        self.assertEqual(len(ranked), 56)  # C(8, 3)
        costs = [r["cost"] for r in ranked]
        self.assertEqual(costs, sorted(costs))

    def test_node_costs_match_registry_classification(self):
        table = {n.name: n for n in qr.node_table()}
        # LIVE + no gate is free; BLOCKED + boss-hands is the priciest.
        self.assertEqual(table["Notion"].cost, 0)
        self.assertEqual(table["Hermes"].cost, 10)
        self.assertLess(table["GitHub"].cost, table["Supabase"].cost)


class TestQAOAOnAer(unittest.TestCase):
    def test_route_in_top5(self):
        result = qr.solve_qaoa(shots=2048, reps=3, seed=1234)
        self.assertEqual(result["backend"], "aer_simulator")
        self.assertTrue(result["backend_is_simulator"])
        chosen = result["chosen_route"]
        self.assertEqual(len(chosen), qr.ROUTE_SIZE)
        self.assertEqual(len(set(chosen)), qr.ROUTE_SIZE)
        ranked = qr.brute_force()
        better = sum(1 for r in ranked if r["cost"] < result["chosen_route_cost"])
        self.assertLessEqual(
            better,
            4,
            f"chosen route {chosen} cost {result['chosen_route_cost']} "
            f"has {better} strictly better subsets (outside top 5)",
        )


if __name__ == "__main__":
    unittest.main()
