# Feedback Loops in Institutional AI — Agent-Based Simulation

Interactive web simulation demonstrating how structural inequality becomes
embedded in algorithmic recommendations through repeated feedback cycles.
Three actors — job-seekers, an HR department, and a platform recommender —
interact over multiple iterations. Small initial biases in institutional
evaluation compound through user adaptation and platform learning, producing
stable inequality even when no actor intends discrimination.

## Run

```bash
python run_server.py
```

Open http://localhost:8080 in your browser. No dependencies beyond Python 3.10+.

## Parameters

**Job-Seeker**
- **Trust in algorithm (T_user)**: probability of following the platform's recommendation vs own preference.
- **Adaptation speed (A_user)**: how fast a user's internal preference shifts toward what they are shown.
- **Risk tolerance (R_user)**: probability of exploring the opposite vacancy level even when trusting the algorithm.

**HR Department**
- **Trust in model (T_hr)**: reliance on the model score vs the human/institutional evaluation.
- **Institutional bias (B_hr)**: penalty applied to Group B in the human evaluation component.

**Platform**
- **Learning rate (LR)**: speed at which the recommender updates its group-level exposure probabilities.
- **Diversity regularization (D)**: pulls exposure toward 50/50 each iteration, resisting collapse.

**Simulation**
- **Feedback weight (FW)**: blend of user-behavior signal (FW=1) vs HR-acceptance signal (FW=0).
- **Iterations**: number of feedback cycles.
- **N agents**: total population size.
- **Group imbalance (G)**: P(group=A). G=0.5 means equal groups.

## Interpreting results

**Collapse (lock-in)**: exposure disparity grows monotonically, reinforcement index stays positive,
Group B converges to near-zero high-level exposure. Caused by high T_user + high A_user + high LR + low D.

**Stabilization / resistance**: disparity stays bounded or shrinks. Achieved by raising D,
lowering LR, lowering FW (so HR acceptance — which may be fairer — dominates the signal),
or lowering T_user (users ignore biased recommendations).
