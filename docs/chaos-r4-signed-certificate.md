# Certified Barrier — Signed R4 Empirical Impossibility

**ID:** `chaos-01-test-no-separation`  ·  **Domain:** dynamical-systems/chaos-classification  ·  **Rung:** R4 (empirical-robust)

## Claim (impossibility)

> The 0-1 test for chaos does not separate conservative (Hamiltonian) from dissipative dynamical systems; the discriminator is phase-space volume contraction (Sigma-lambda = sum of Lyapunov exponents: 0 for Hamiltonian, <0 for dissipative).

*Negation of:* a 0-1 test statistic that reliably classifies conservative vs dissipative chaos

## Human sign-off (the named correctness anchor)

| field | value |
|---|---|
| reviewer | **Melissa Ellison** |
| date | 2026-06-22 |
| kind | human |
| verdict | **adequate** |

> Author sign-off: the 12 answers trace to the chaos-universality-paper findings and adequately address every generated stress question. Correctness anchored by this named human verdict -- never by automation.

## Stress contract — the 12 generated questions and your answers

### constraint: `energy_order`

**Q1. What maintains order?**

In a conservative (Hamiltonian) system phase-space volume is exactly preserved (Liouville's theorem): Sigma-lambda = 0. Nothing external maintains it; the dynamics conserve it.

**Q2. Where is energy entering?**

The studied systems are autonomous in steady state; the discriminating flow is phase-space volume contraction (Sigma-lambda), not energy input. This is exactly the contraction the 0-1 K-statistic does not measure.

**Q3. Where is energy being lost?**

Dissipative systems contract phase-space volume at rate Sigma-lambda < 0 (sum of Lyapunov exponents); Hamiltonian systems have Sigma-lambda = 0. Measured across 11 dissipative (Sigma-lambda<0) and 8 Hamiltonian (Sigma-lambda=0) systems.

**Q4. What happens when maintenance stops?**

Not applicable to these autonomous systems; the conservative/dissipative split is a structural volume-contraction property (Sigma-lambda), independent of any maintenance process -- and the 0-1 statistic is blind to it.

### constraint: `model_degeneracy`

**Q5. Do other models predict the same observations?**

Yes, and that is the finding: the 0-1 test and Sigma-lambda disagree on the separation, and Sigma-lambda is the one that holds. The Green-Kubo closed form predicts the 0-1 curve (r=0.955), showing the 0-1 signal tracks a mixing-rate quantity, not conservation.

**Q6. What independent observable would distinguish between models?**

Sigma-lambda = sum of Lyapunov exponents (phase-space volume contraction): exactly 0 for Hamiltonian, strictly < 0 for dissipative. Conservation-grounded and independent of the 0-1 K-statistic.

**Q7. How many free parameters were fitted?**

Zero in the Sigma-lambda discriminator (read directly from the Lyapunov spectrum). The retracted 0-1 separation carried one hidden parameter: trajectory length.

**Q8. Has the model been tested on data not used to tune it?**

Yes -- this is the crux. The original 0-1 separation was a SHORT-TRAJECTORY ARTIFACT that vanished on longer trajectories and was retracted. Sigma-lambda was verified across 8 Hamiltonian (Sigma-lambda=0), 11 dissipative (Sigma-lambda<0), and Mackey-Glass (delay system; Sigma-lambda correctly nan).

### constraint: `hidden_variable`

**Q9. What variable is not being measured?**

Trajectory length -- the hidden variable behind the spurious 0-1 separation; the K-statistic conflated transient mixing with conservation.

**Q10. What assumption may be false?**

The assumption that the 0-1 growth statistic reflects conservation. It reflects mixing rate, not phase-space volume behavior; this is what the retraction corrected.

**Q11. What would explain the contradiction?**

Sigma-lambda explains it: conservation is a volume-contraction property (0 vs <0) that the 0-1 test does not measure. Green-Kubo links the 0-1 curve to a dynamical (not conservation) quantity, r=0.955.

**Q12. What data would reveal the missing variable?**

Trajectory / run-length sweeps: the 0-1 separation degrades with length (documented in the run-length calculator appendix), while Sigma-lambda is stable under the same sweeps.

## Trusted base (what you are trusting, named)

- a structured stress contract: every generated stress question answered AND adequacy-screened (cites concrete evidence, non-circular)
- the empirical evidence cited in each answer (Sigma-lambda across 8 Hamiltonian + 11 dissipative systems; Green-Kubo r=0.955; the retracted short-trajectory artifact)
- a NAMED human sign-off on answer correctness -- the irreducible anchor, never automated

## One-directional guarantee

claim-stress can only REFUSE (an unanswered or weak/dodging answer) or DEFER (no named human sign-off); it can never grant R4 from automation alone. Answer correctness is anchored by a named human reviewer -- automating that verdict with a model would be rung-laundering, the one move the atlas refuses.

---
*Rendered from `barriers/chaos-01-test-no-separation.barrier.json`. Re-checkable with `python3 tools/barrier_check.py`.*
