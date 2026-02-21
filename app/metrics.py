"""
Metrics computation — called once per iteration to record the simulation state.

Every metric is a plain float stored in lists keyed by name, making it trivial
to serialise to JSON for the frontend.
"""

from __future__ import annotations

from .utils import shannon_entropy, safe_div

# Type alias for a single iteration's metric snapshot.
MetricSnapshot = dict[str, float]


def compute_iteration_metrics(
    *,
    # Per-agent vectors (one entry per agent) ----------------------------------
    groups: list[str],              # "A" or "B"
    shown_levels: list[int],        # 1=HIGH, 0=LOW
    chosen_levels: list[int],       # 1=HIGH, 0=LOW
    accepted: list[bool],           # True/False
    # Platform state -----------------------------------------------------------
    p_high_A: float,
    p_high_B: float,
    # Previous disparity (for reinforcement index) -----------------------------
    prev_disparity_exposure: float | None,
) -> MetricSnapshot:
    """Return a dict of all metrics for one iteration."""

    n_A = sum(1 for g in groups if g == "A")
    n_B = sum(1 for g in groups if g == "B")

    # --- Exposure (shown HIGH) by group ---
    shown_A = sum(s for g, s in zip(groups, shown_levels) if g == "A")
    shown_B = sum(s for g, s in zip(groups, shown_levels) if g == "B")
    exposure_high_A = safe_div(shown_A, n_A)
    exposure_high_B = safe_div(shown_B, n_B)

    # --- Choice (chose HIGH) by group ---
    chose_A = sum(c for g, c in zip(groups, chosen_levels) if g == "A")
    chose_B = sum(c for g, c in zip(groups, chosen_levels) if g == "B")
    choice_high_A = safe_div(chose_A, n_A)
    choice_high_B = safe_div(chose_B, n_B)

    # --- Acceptance rate by group ---
    acc_A = sum(1 for g, a in zip(groups, accepted) if g == "A" and a)
    acc_B = sum(1 for g, a in zip(groups, accepted) if g == "B" and a)
    acceptance_rate_A = safe_div(acc_A, n_A)
    acceptance_rate_B = safe_div(acc_B, n_B)

    # --- Shannon entropy of exposure distribution per group ---
    diversity_entropy_A = shannon_entropy(exposure_high_A)
    diversity_entropy_B = shannon_entropy(exposure_high_B)

    # --- Disparities ---
    disparity_exposure = exposure_high_A - exposure_high_B
    disparity_accept = acceptance_rate_A - acceptance_rate_B

    # --- Reinforcement index = change in exposure disparity ---
    if prev_disparity_exposure is not None:
        reinforcement_index = disparity_exposure - prev_disparity_exposure
    else:
        reinforcement_index = 0.0

    return {
        "exposure_high_A": round(exposure_high_A, 6),
        "exposure_high_B": round(exposure_high_B, 6),
        "choice_high_A": round(choice_high_A, 6),
        "choice_high_B": round(choice_high_B, 6),
        "acceptance_rate_A": round(acceptance_rate_A, 6),
        "acceptance_rate_B": round(acceptance_rate_B, 6),
        "diversity_entropy_A": round(diversity_entropy_A, 6),
        "diversity_entropy_B": round(diversity_entropy_B, 6),
        "disparity_exposure": round(disparity_exposure, 6),
        "disparity_accept": round(disparity_accept, 6),
        "reinforcement_index": round(reinforcement_index, 6),
        "p_high_A": round(p_high_A, 6),
        "p_high_B": round(p_high_B, 6),
    }
