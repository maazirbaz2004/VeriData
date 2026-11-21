"""Fixed registry of callable statistical test tools (Phase 3 Section 4.5, Principle P6)."""

from __future__ import annotations

from veridata.contracts.hypothesis import RelationshipType
from veridata.stats.tests_categorical import (
    run_chi_square,
    run_fisher_exact,
    run_monte_carlo_chi_square,
)
from veridata.stats.tests_numeric_binary import run_mann_whitney_u, run_welch_t
from veridata.stats.tests_numeric_categorical import run_kruskal_wallis, run_welch_anova
from veridata.stats.tests_numeric_numeric import run_pearson, run_spearman
from veridata.stats.types import ToolSpec

REGISTRY: dict[str, ToolSpec] = {
    "welch_t": ToolSpec(
        name="welch_t",
        relationship=RelationshipType.NUM_BINARY,
        run=run_welch_t,
        effect_name="hedges_g",
        description="Two-sided Welch's t-test comparing means across two groups (unequal variances allowed).",
    ),
    "mann_whitney_u": ToolSpec(
        name="mann_whitney_u",
        relationship=RelationshipType.NUM_BINARY,
        run=run_mann_whitney_u,
        effect_name="rank_biserial",
        description="Two-sided non-parametric Mann-Whitney U rank test comparing two groups.",
    ),
    "welch_anova": ToolSpec(
        name="welch_anova",
        relationship=RelationshipType.NUM_CATEGORICAL,
        run=run_welch_anova,
        effect_name="eta_squared",
        description="Welch's one-way ANOVA comparing means across k >= 3 groups (unequal variances allowed).",
    ),
    "kruskal_wallis": ToolSpec(
        name="kruskal_wallis",
        relationship=RelationshipType.NUM_CATEGORICAL,
        run=run_kruskal_wallis,
        effect_name="epsilon_squared",
        description="Non-parametric Kruskal-Wallis H test comparing distributions across k >= 3 groups.",
    ),
    "pearson": ToolSpec(
        name="pearson",
        relationship=RelationshipType.NUM_NUM,
        run=run_pearson,
        effect_name="pearson_r",
        description="Two-sided Pearson product-moment linear correlation between two numeric variables.",
    ),
    "spearman": ToolSpec(
        name="spearman",
        relationship=RelationshipType.NUM_NUM,
        run=run_spearman,
        effect_name="spearman_rho",
        description="Two-sided Spearman rank monotonic correlation between two numeric variables.",
    ),
    "chi_square": ToolSpec(
        name="chi_square",
        relationship=RelationshipType.CAT_CAT,
        run=run_chi_square,
        effect_name="cramers_v_bc",
        description="Pearson chi-square test of independence for contingency tables.",
    ),
    "fisher_exact": ToolSpec(
        name="fisher_exact",
        relationship=RelationshipType.CAT_CAT,
        run=run_fisher_exact,
        effect_name="cramers_v_bc",
        description="Two-sided Fisher's exact test for sparse or small-n 2x2 contingency tables.",
    ),
    "monte_carlo_chi_square": ToolSpec(
        name="monte_carlo_chi_square",
        relationship=RelationshipType.CAT_CAT,
        run=run_monte_carlo_chi_square,
        effect_name="cramers_v_bc",
        description="Seeded permutation (Monte Carlo) chi-square test for sparse r x c tables.",
    ),
}

