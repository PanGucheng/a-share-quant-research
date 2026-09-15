"""Write the one human-specified E3 policy before reading any B494 scores."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/economic_translation_mvp/e3_freeze_v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sources = {
        "proposal": Path("D:/Download/给 Codex：E3 Strategy Freeze Preparation 与 Outcome-Blind 结构预验收.md"),
        "plan": ROOT / "docs/ECONOMIC_E3_FREEZE_PREPARATION.md",
        "scores": ROOT / "reports/economic_translation_mvp/e1_inputs.json",
        "e1": ROOT / "reports/economic_translation_mvp/e1_completion_v1/REPORT.md",
        "capital": ROOT / "reports/economic_translation_mvp/small_capital_v1/REPORT.md",
        "core": ROOT / "reports/economic_translation_mvp/e2_hard_closure_v1/HISTORICAL_CORE_ACCEPTANCE.json",
        "fees": ROOT / "reports/economic_translation_mvp/dated_fee_schedule.csv",
    }
    rules = dict(
        signal=dict(arm="Broad494", start="2015-01-05", end="2023-12-29",
                    rank="score_desc_then_original_instrument_asc", rank_before_eligibility=True,
                    universe="same_day_sealed_keys", exchanges=["SH", "SZ"],
                    star_access=True, chinext_access=True),
        schedule=dict(interval=5, anchor_index=0, execute="next_calendar_session_open_reference",
                      reset_at_year_boundary=False, final_signal_without_next_session="no_order"),
        membership=dict(k=8, entry_rank=8, hold_rank=16, max_normal_exits=1,
                        max_normal_entries=1, cold_start="first_scheduled_decision_only_up_to_8",
                        missing_rank="worst_exit_priority", minimum_holding_sessions=0,
                        priority="absent_first_then_rank_desc_then_instrument_asc"),
        orders=dict(sell_before_buy=True, blocked_or_partial_sell="no_new_buy_this_decision",
                    slot_release="full_sale_and_no_pending_right", entry_gate="E2_ALLOW_ENTRY",
                    missing_gate="deny", holding_gate="E2_HALT_RETAIN_or_CARRY_or_ORDINARY",
                    gate_rejection="next_within_original_top8", opening_failure="no_intraday_reselection",
                    failed_exit="no_second_exit_attempt", intent_expiry="session_end",
                    unspent_attempts="do_not_accumulate", cash_receivable_spendable=False),
        slots=dict(max_identities=8, includes=["shares", "unlisted_bonus", "registered_right", "cash_receivable"],
                   alias_new="reject_duplicate_economic_identity", alias_held="halt_retain"),
        sizing=dict(initial_cash_cny=100000, cash_reserve=0.05, weighting="near_equal_new_identity_only",
                    base="A_certified_assets_excluding_receivables_and_unlisted_rights",
                    per_entry_all_in_budget="0.95*base/8",
                    cash_ceiling="max(0,actual_spendable_cash-0.05*base)",
                    quantity_reference="prior_signal_close", opening="only_check_or_reduce_never_increase",
                    retained_reweight=False, partial_topup=False, leftover_redistribution=False),
        fees=dict(commission_rate=0.00025, minimum_commission_cny=5,
                  commission_bundle="exchange_handling_and_regulatory_included_stamp_transfer_separate",
                  mother_order="instrument_session_side", rounding="HALF_UP_cent_per_cumulative_component",
                  stamp_sell=[dict(start="2015-01-01", rate=0.001), dict(start="2023-08-28", rate=0.0005)],
                  transfer=[dict(start="2015-01-01", end="2015-07-31", SH=0.0003, SZ=0.0000255,
                                 SH_basis="shares_times_verified_par_value", SZ_basis="consideration"),
                            dict(start="2015-08-01", end="2022-04-28", rate=0.00002),
                            dict(start="2022-04-29", end="2023-12-29", rate=0.00001)],
                  early_minimum_cny=0, early_pass_through="separate_assumption", missing_par_value="block",
                  implicit_bps_per_side=10, implicit_mode="cash_cost_not_changed_open_price"),
        execution=dict(adv_prior_sessions=20, adv_cap=0.01, missing_adv="no_new_entry",
                       warmup="2014-12-04_through_2014-12-31_only", open_fallback=False,
                       state_mode="historical_session_effective_known_at_null",
                       lot="existing_dated_board_lot_quantity", t_plus_one=True),
        continuity=dict(daily_processing=True, annual_reset=False, pending_rights_persist=True,
                        on_unresolved_exposure="HALT_RETAIN_then_NOT_REACHED",
                        final_boundary="open_rights_and_right_censored_no_liquidation",
                        persistence="whole_day_commit_state_and_confirmations_no_duplicate_replay",
                        dividend="gross_tax_approximation", generic_R_cleanup=False),
        benchmark=dict(external_name="中证全指价格指数", external_code="000985",
                       external_role="noninvestable_market_context_price_only_not_net_total_return_alpha",
                       official_method="https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/20231208175438-000985_Index_Methodology_cn.pdf",
                       internal="PIT_executable_universe_EW_research_reference_design_deferred",
                       benchmark_values_authorized=False),
        preflight=dict(candidate_count=1, grids=False, target_scope="2015-2023_all_sealed_score_sessions",
                       target_role="ideal_membership_projection_not_actual_exposure",
                       actual_probe="first_signal_top8_next_session_only",
                       actual_unmeasured="null_not_zero", parameters_may_change_after_results=False,
                       long_scans="user_run_only_no_recollection", outcome_access=False, e4=False),
    )
    basis = {
        "signal": (["scores", "proposal"], "research_definition", True),
        "schedule": (["proposal", "e1"], "research_definition_not_optimality_claim", True),
        "membership": (["proposal", "capital", "e1"], "human_prespecified_research_definition", True),
        "orders": (["core", "plan"], "conservative_engineering_constraint", True),
        "slots": (["core", "plan"], "accounting_constraint", False),
        "sizing": (["proposal", "capital", "plan"], "user_capital_and_research_definition", True),
        "fees": (["fees", "capital", "plan"], "user_commission_dated_rules_and_early_approximation", True),
        "execution": (["core", "plan"], "existing_MVP_execution_contract", True),
        "continuity": (["core", "plan"], "accounting_and_accepted_MVP_contract", True),
        "benchmark": (["proposal", "plan"], "research_reference_identity_only", True),
        "preflight": (["proposal", "plan"], "authorization_and_evidence_boundary", False),
    }
    value = dict(strategy_id="economic_e3_b494_100k_k8_h16_d5_drop1_v1", baseline="33c43bd",
                 status="E3 STRATEGY FROZEN / PATH PREFLIGHT PENDING", rules=rules,
                 sources={k: dict(path=str(p), sha256=sha(p)) for k, p in sources.items()},
                 provenance={k: dict(sources=s, classification=c, mvp_approximation=a)
                             for k, (s, c, a) in basis.items()},
                 research_context="retrospective_development_prior_D3A_opened_this_turn_no_outcomes")
    REPORT.mkdir(exist_ok=True)
    with (REPORT / "freeze.json").open("x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    with (REPORT / "freeze.sha256").open("x", encoding="ascii") as f:
        f.write(sha(REPORT / "freeze.json") + "\n")
    print("Single E3 definition frozen before score access:", sha(REPORT / "freeze.json"))


if __name__ == "__main__":
    main()
