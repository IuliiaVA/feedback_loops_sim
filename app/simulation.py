"""
Agent-based simulation of feedback loops in institutional AI hiring.

Three actors interact across iterations:
  1. Platform  — recommends vacancy levels per group
  2. Job-seeker — decides which vacancy to apply to
  3. HR dept   — evaluates applicants with institutional bias

Each iteration produces feedback that updates the platform's model and the
users' internal preferences, creating compounding reinforcement dynamics.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from .metrics import MetricSnapshot, compute_iteration_metrics
from .utils import clamp, safe_div


# ── Data classes for the three actors ─────────────────────────────────────────

@dataclass
class Agent:
    """A single job-seeker agent."""
    group: str                 # "A" or "B"
    skill: float               # innate competence ∈ [0,1]
    trust_in_algorithm: float  # T_user — probability of following the platform
    adaptation_speed: float    # A_user — preference drift rate
    risk_tolerance: float      # R_user — exploration probability
    preference_for_high: float # internal evolving state ∈ [0,1]


@dataclass
class HRDepartment:
    """Institutional gatekeeper."""
    trust_in_model: float      # T_hr — reliance on model score vs human eval
    institutional_bias: float  # B_hr — penalty subtracted from Group B in human eval
    hiring_threshold: float    # θ — minimum combined score
    hiring_capacity: float     # c — fraction of applicants that can be accepted


@dataclass
class Platform:
    """Recommendation engine that learns per-group exposure probabilities."""
    learning_rate: float               # LR
    diversity_regularization: float    # D — pulls p toward 0.5
    feedback_weight: float             # FW — user signal vs HR signal blend
    p_high: dict[str, float] = field(  # p_high_A, p_high_B — learned state
        default_factory=lambda: {"A": 0.5, "B": 0.5}
    )


# ── Simulation parameters ────────────────────────────────────────────────────

@dataclass
class SimParams:
    """All tuneable parameters collected in one place."""
    # Population
    n_agents: int = 200
    group_imbalance: float = 0.5    # G: P(group=A)
    seed: int = 42

    # Job-seeker (applied uniformly; per-agent noise comes from skill variance)
    t_user: float = 0.7
    a_user: float = 0.3
    r_user: float = 0.2

    # HR
    t_hr: float = 0.6
    b_hr: float = 0.15
    hiring_threshold: float = 0.45
    hiring_capacity: float = 0.3

    # Platform
    lr: float = 0.25
    diversity_reg: float = 0.1
    feedback_weight: float = 0.6

    # Simulation control
    iterations: int = 20


# ── Main simulation function ─────────────────────────────────────────────────

def run_simulation(params: SimParams) -> dict[str, Any]:
    """
    Execute the full simulation and return iteration-level metrics plus the
    final platform state.

    Returns a dict with:
        "iterations": list of MetricSnapshot dicts (one per iteration)
        "params":     echo of the input parameters (for the UI)
    """
    rng = random.Random(params.seed)

    # ── 1. Create agents ─────────────────────────────────────────────────
    agents: list[Agent] = []
    for _ in range(params.n_agents):
        group = "A" if rng.random() < params.group_imbalance else "B"
        skill = clamp(rng.gauss(0.5, 0.15))
        # Initial preference correlated with skill (high-skill → prefers HIGH)
        pref = clamp(skill + rng.gauss(0, 0.05))
        agents.append(Agent(
            group=group,
            skill=skill,
            trust_in_algorithm=params.t_user,
            adaptation_speed=params.a_user,
            risk_tolerance=params.r_user,
            preference_for_high=pref,
        ))

    # ── 2. Create HR and Platform ────────────────────────────────────────
    hr = HRDepartment(
        trust_in_model=params.t_hr,
        institutional_bias=params.b_hr,
        hiring_threshold=params.hiring_threshold,
        hiring_capacity=params.hiring_capacity,
    )
    platform = Platform(
        learning_rate=params.lr,
        diversity_regularization=params.diversity_reg,
        feedback_weight=params.feedback_weight,
    )

    # ── 3. Iteration loop ────────────────────────────────────────────────
    history: list[MetricSnapshot] = []
    prev_disparity: float | None = None

    for _t in range(params.iterations):
        groups: list[str] = []
        shown_levels: list[int] = []
        chosen_levels: list[int] = []
        accepted_flags: list[bool] = []

        # Temporary accumulators for feedback signal computation
        user_chose_high: dict[str, list[int]] = {"A": [], "B": []}
        hr_accepted_high: dict[str, list[bool]] = {"A": [], "B": []}

        # Per-agent scoring for HR capacity cap (collect all, then rank)
        applicant_records: list[dict] = []

        for agent in agents:
            g = agent.group
            groups.append(g)

            # ── STEP 1: Platform exposure ────────────────────────────────
            #   Base probability from learned model
            p_base = platform.p_high[g]
            #   Diversity regularization pulls toward 0.5 (uniform exposure)
            #   D=1 → always show 50/50; D=0 → pure model
            p_final = (1.0 - platform.diversity_regularization) * p_base \
                      + platform.diversity_regularization * 0.5
            p_final = clamp(p_final)
            shown_high = 1 if rng.random() < p_final else 0
            shown_levels.append(shown_high)

            # ── STEP 2: User action (click / apply decision) ─────────────
            if rng.random() < agent.trust_in_algorithm:
                # User trusts the algorithm → follows shown level ...
                if rng.random() < agent.risk_tolerance:
                    # ... but explores the opposite with probability R_user
                    chosen = 1 - shown_high
                else:
                    chosen = shown_high
            else:
                # User ignores algorithm → chooses based on internal preference
                chosen = 1 if rng.random() < agent.preference_for_high else 0
            chosen_levels.append(chosen)

            user_chose_high[g].append(chosen)

            # ── STEP 3: HR evaluation ────────────────────────────────────
            #   model_score = skill (unbiased algorithmic assessment)
            model_score = agent.skill
            #   human_score = skill - B_hr for group B (institutional bias)
            human_score = agent.skill - (hr.institutional_bias if g == "B" else 0.0)
            #   Blend: T_hr weights model, (1-T_hr) weights biased human eval
            final_score = hr.trust_in_model * model_score \
                          + (1.0 - hr.trust_in_model) * human_score

            # Record for capacity-capped ranking
            applicant_records.append({
                "idx": len(applicant_records),
                "group": g,
                "final_score": final_score,
                "chosen_high": chosen,
                "meets_threshold": final_score >= hr.hiring_threshold,
            })

        # ── Apply hiring capacity cap (rank then accept top c fraction) ──
        eligible = [r for r in applicant_records if r["meets_threshold"]]
        # Sort by final_score descending — top candidates accepted first
        eligible.sort(key=lambda r: r["final_score"], reverse=True)
        max_accept = max(1, int(hr.hiring_capacity * len(applicant_records)))
        accepted_set: set[int] = set()
        for r in eligible[:max_accept]:
            accepted_set.add(r["idx"])

        for r in applicant_records:
            is_accepted = r["idx"] in accepted_set
            accepted_flags.append(is_accepted)

            g = r["group"]
            # HR signal: was this applicant to HIGH accepted?
            if r["chosen_high"] == 1:
                hr_accepted_high[g].append(is_accepted)

        # ── STEP 4: Platform feedback update ─────────────────────────────
        for g in ("A", "B"):
            # user_signal = fraction of group g that chose HIGH
            u_list = user_chose_high[g]
            user_signal = safe_div(sum(u_list), len(u_list))

            # hr_signal = fraction of group g HIGH applicants that were accepted
            h_list = hr_accepted_high[g]
            hr_signal = safe_div(sum(h_list), len(h_list)) if h_list else user_signal

            # Combine signals: FW blends user behavior vs HR acceptance
            observed = platform.feedback_weight * user_signal \
                       + (1.0 - platform.feedback_weight) * hr_signal

            # Exponential moving average update
            # LR controls how fast the platform "forgets" its prior belief
            platform.p_high[g] = clamp(
                (1.0 - platform.learning_rate) * platform.p_high[g]
                + platform.learning_rate * observed
            )

        # ── STEP 5: User preference update (internalization) ─────────────
        for agent, shown in zip(agents, shown_levels):
            observed_level = float(shown)  # 1.0 if shown HIGH, 0.0 if LOW
            # A_user controls how fast the user internalizes algorithmic exposure
            # High A_user → preference rapidly converges to whatever is shown
            agent.preference_for_high = clamp(
                (1.0 - agent.adaptation_speed) * agent.preference_for_high
                + agent.adaptation_speed * observed_level
            )

        # ── Record metrics ───────────────────────────────────────────────
        snapshot = compute_iteration_metrics(
            groups=groups,
            shown_levels=shown_levels,
            chosen_levels=chosen_levels,
            accepted=accepted_flags,
            p_high_A=platform.p_high["A"],
            p_high_B=platform.p_high["B"],
            prev_disparity_exposure=prev_disparity,
        )
        prev_disparity = snapshot["disparity_exposure"]
        history.append(snapshot)

    return {
        "iterations": history,
        "params": {
            "n_agents": params.n_agents,
            "group_imbalance": params.group_imbalance,
            "seed": params.seed,
            "t_user": params.t_user,
            "a_user": params.a_user,
            "r_user": params.r_user,
            "t_hr": params.t_hr,
            "b_hr": params.b_hr,
            "hiring_threshold": params.hiring_threshold,
            "hiring_capacity": params.hiring_capacity,
            "lr": params.lr,
            "diversity_reg": params.diversity_reg,
            "feedback_weight": params.feedback_weight,
            "iterations": params.iterations,
        },
    }
