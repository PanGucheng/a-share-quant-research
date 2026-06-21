"""Point-in-time market context adapters for factor evaluation."""

from factor_research.context.benchmark import load_benchmark_returns
from factor_research.context.evaluation import (
    attach_benchmark_relative_returns,
    attach_context,
    build_context_keys,
    context_coverage,
    load_benchmark_context,
)
from factor_research.context.listing import attach_listing_age, listing_age_as_of, listing_dates
from factor_research.context.universe import (
    active_members,
    attach_membership,
    load_instrument_intervals,
    membership_counts,
)

__all__ = [
    "active_members",
    "attach_listing_age",
    "attach_membership",
    "attach_benchmark_relative_returns",
    "attach_context",
    "build_context_keys",
    "context_coverage",
    "listing_age_as_of",
    "listing_dates",
    "load_benchmark_returns",
    "load_benchmark_context",
    "load_instrument_intervals",
    "membership_counts",
]
