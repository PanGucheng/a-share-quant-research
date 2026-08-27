from __future__ import annotations

from typing import Any

import pandas as pd

from factor_universe_v2.mature_factors import (
    DAILY_BASIC_FACTOR_NAMES,
    FUNDAMENTAL_FACTOR_NAMES,
    MARKET_FACTOR_NAMES,
    MONEYFLOW_FACTOR_NAMES,
)


SOURCES = {
    "a_share_review": "https://doi.org/10.1016/j.pacfin.2021.101607",
    "china_size_value": "https://www.nber.org/papers/w24458",
    "worldquant101": "https://arxiv.org/abs/1601.00991",
    "qlib": "https://qlib.readthedocs.io/en/latest/advanced/alpha.html",
    "barra": "https://www.msci.com/documents/1296102/1636401/MSCI_Barra_Market%2BEquity%2BModels_Factsheet%2B.pdf/0c9d381f-e4e6-42fc-b7c2-dfff694dd650",
    "amihud": "https://doi.org/10.1016/S1386-4181(01)00024-6",
    "china_liquidity": "https://doi.org/10.1108/20441391111092264",
    "china_order_imbalance": "https://doi.org/10.1016/j.qref.2007.09.004",
    "gross_profitability": "https://www.nber.org/papers/w15940",
    "accruals": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2598",
    "high_52w": "https://doi.org/10.1111/j.1540-6261.2004.00695.x",
    "parkinson": "https://doi.org/10.1086/296071",
}


def _row(
    name: str,
    family: str,
    subfamily: str,
    definition: str,
    rationale: str,
    fields: str,
    source_keys: tuple[str, ...],
    adapter: str,
    *,
    evidence_tier: str = "A",
) -> dict[str, Any]:
    return {
        "factor_name": name,
        "source": "academic_and_industry_mature",
        "source_family": "MaturePublic",
        "source_citations": ";".join(SOURCES[key] for key in source_keys),
        "definition": definition,
        "economic_rationale": rationale,
        "required_fields": fields,
        "economic_family": family,
        "economic_subfamily": subfamily,
        "secondary_family": "",
        "pit_implications": "row_t_after_close_usable_next_session" if family not in {"Profitability", "Quality", "GrowthInvestment", "Leverage", "CashFlow", "Value"} else "statement_revision_available_by_decision_date;market_cap_row_t_after_close",
        "evidence_tier": evidence_tier,
        "implementation_status": "authoritative_v2",
        "compute_adapter": adapter,
        "candidate_decision": "admit",
        "decision_reason": "mature_definition_new_economic_axis_data_and_pit_proven",
    }


def build_mature_factor_inventory() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    market_specs = {
        "mature_momentum_12_1": ("MomentumTrend", "IntermediateMomentum", "close[t-21]/close[t-252]-1", "Intermediate-horizon price persistence with the most recent month skipped.", "$close,$market_return,$open,$high,$low,$amount,$vwap", ("a_share_review", "barra")),
        "mature_reversal_1m": ("Reversal", "ShortTermReversal", "-(close/close[t-21]-1)", "Captures the short-horizon reversal documented as unusually relevant in A shares.", "$close,$market_return,$open,$high,$low,$amount,$vwap", ("a_share_review", "barra")),
        "mature_high_52w": ("MomentumTrend", "PriceAnchor", "close/rolling_max_252(close)", "Distance from the 52-week high is a mature price-anchor signal.", "$close,$market_return,$open,$high,$low,$amount,$vwap", ("high_52w", "a_share_review")),
        "mature_overnight_return_20": ("Reversal", "Overnight", "mean_20(open/previous_close-1)", "Separates overnight information and retail-driven price pressure from the intraday leg.", "$open,$close,$market_return,$high,$low,$amount,$vwap", ("a_share_review",)),
        "mature_intraday_return_20": ("TradingBehavior", "Intraday", "mean_20(close/open-1)", "Separates within-session price pressure from overnight moves.", "$open,$close,$market_return,$high,$low,$amount,$vwap", ("a_share_review",)),
        "mature_max_daily_return_21": ("VolatilityRisk", "LotteryPreference", "max_21(daily_return)", "Recent maximum return captures lottery-like payoff exposure.", "$close,$market_return,$open,$high,$low,$amount,$vwap", ("barra", "a_share_review")),
        "mature_realized_volatility_60": ("VolatilityRisk", "TotalVolatility", "std_60(daily_return)", "Mature total-risk exposure and A-share risk-anomaly candidate.", "$close,$market_return,$open,$high,$low,$amount,$vwap", ("barra", "a_share_review")),
        "mature_downside_volatility_60": ("VolatilityRisk", "DownsideRisk", "std_60(negative_daily_returns)", "Focuses on adverse rather than symmetric return variation.", "$close,$market_return,$open,$high,$low,$amount,$vwap", ("barra", "a_share_review")),
        "mature_return_skewness_60": ("VolatilityRisk", "HigherMoment", "skew_60(daily_return)", "Captures asymmetric lottery and crash-like return distributions.", "$close,$market_return,$open,$high,$low,$amount,$vwap", ("barra",)),
        "mature_parkinson_volatility_20": ("VolatilityRisk", "RangeVolatility", "sqrt(mean_20(log(high/low)^2)/(4*log(2)))", "Uses the intraday range for a mature volatility estimator.", "$high,$low,$close,$market_return,$open,$amount,$vwap", ("parkinson",)),
        "mature_max_drawdown_60": ("VolatilityRisk", "Drawdown", "min_60(close/running_max(close)-1)", "Measures realized path-dependent downside exposure.", "$close,$market_return,$open,$high,$low,$amount,$vwap", ("barra",)),
        "mature_amihud_illiquidity_20": ("Liquidity", "VolumePriceImpact", "mean_20(abs(return)/amount_cny)", "Daily price response per currency volume is a classic low-frequency price-impact proxy.", "$amount,$close,$market_return,$open,$high,$low,$vwap", ("amihud", "china_liquidity")),
        "mature_amount_momentum_20": ("Liquidity", "AmountState", "amount/mean(previous_20_amount)-1", "Detects abnormal trading value without substituting share volume for amount.", "$amount,$close,$market_return,$open,$high,$low,$vwap", ("worldquant101", "a_share_review")),
        "mature_vwap_deviation": ("TradingBehavior", "VWAPDeviation", "close/vwap-1", "Direct canonical close-to-VWAP pressure measure.", "$vwap,$close,$market_return,$open,$high,$low,$amount", ("worldquant101", "qlib")),
        "mature_vwap_deviation_20": ("TradingBehavior", "VWAPDeviation", "mean_20(close/vwap-1)", "Persistent close-to-VWAP pressure rather than a volume proxy.", "$vwap,$close,$market_return,$open,$high,$low,$amount", ("worldquant101", "qlib")),
        "mature_market_beta_60": ("VolatilityRisk", "MarketBeta", "cov_60(stock_return,market_return)/var_60(market_return)", "Systematic market-risk exposure used by mature industrial factor models.", "$close,$market_return,$open,$high,$low,$amount,$vwap", ("barra",)),
        "mature_idiosyncratic_volatility_60": ("VolatilityRisk", "ResidualVolatility", "std_60(stock_return-beta_60*market_return)", "Residual risk is distinct from total volatility and has A-share-specific evidence.", "$close,$market_return,$open,$high,$low,$amount,$vwap", ("barra", "a_share_review")),
    }
    for name in MARKET_FACTOR_NAMES:
        rows.append(_row(name, *market_specs[name], "factor_universe_v2.mature_factors.compute_market_factors"))

    basic_specs = {
        "mature_log_total_market_cap": ("Size", "TotalSize", "log(total_mv)", "Canonical size exposure.", "total_mv", ("china_size_value", "barra")),
        "mature_log_float_market_cap": ("Size", "FloatSize", "log(circ_mv)", "Tradable-float size is distinct in the partially floating A-share market.", "circ_mv", ("china_size_value", "barra")),
        "mature_float_market_cap_ratio": ("Size", "FloatStructure", "circ_mv/total_mv", "Captures the tradable-float share of company value.", "circ_mv,total_mv", ("china_size_value",)),
        "mature_earnings_yield_ttm": ("Value", "EarningsYield", "1/pe_ttm for positive pe_ttm", "Earnings-to-price is the preferred China value signal in the CH-3 evidence.", "pe_ttm", ("china_size_value", "a_share_review")),
        "mature_book_to_price": ("Value", "BookToPrice", "1/pb for positive pb", "Classic value exposure retained as a separate candidate.", "pb", ("china_size_value", "a_share_review")),
        "mature_sales_to_price_ttm": ("Value", "SalesToPrice", "1/ps_ttm for positive ps_ttm", "Sales-based value is less affected by negative earnings.", "ps_ttm", ("a_share_review", "barra")),
        "mature_dividend_yield_ttm": ("Value", "DividendYield", "dv_ttm/100", "Mature shareholder-yield component.", "dv_ttm", ("barra", "a_share_review")),
        "mature_turnover_rate_free_float": ("Liquidity", "Turnover", "turnover_rate_f/100", "Turnover is specifically supported as a China-market liquidity proxy.", "turnover_rate_f", ("china_liquidity", "china_size_value")),
        "mature_turnover_mean_20": ("Liquidity", "TurnoverLevel", "mean_20(turnover_rate_f/100)", "Persistent turnover level captures liquidity and speculative trading.", "turnover_rate_f", ("china_liquidity", "china_size_value")),
        "mature_turnover_volatility_20": ("Liquidity", "LiquidityVolatility", "std_20(turnover_rate_f/100)", "Separates unstable liquidity from average liquidity.", "turnover_rate_f", ("a_share_review",)),
        "mature_abnormal_turnover_20": ("TradingBehavior", "AbnormalTurnover", "turnover_t/mean(previous_20_turnover)-1", "Abnormal turnover is a China-specific sentiment/trading axis.", "turnover_rate_f", ("china_size_value",)),
        "mature_volume_ratio": ("Liquidity", "RelativeVolume", "Tushare volume_ratio", "Provider-defined current-to-recent volume ratio.", "volume_ratio", ("a_share_review",)),
    }
    for name in DAILY_BASIC_FACTOR_NAMES:
        rows.append(_row(name, *basic_specs[name], "factor_universe_v2.mature_factors.compute_daily_basic_factors"))

    money_specs = {
        "mature_overall_order_imbalance": ("TradingBehavior", "OrderImbalance", "(all_buy_amount-all_sell_amount)/(all_buy_amount+all_sell_amount)"),
        "mature_small_order_imbalance": ("TradingBehavior", "RetailFlow", "(small_buy-small_sell)/(small_buy+small_sell)"),
        "mature_medium_order_imbalance": ("TradingBehavior", "MediumOrderFlow", "(medium_buy-medium_sell)/(medium_buy+medium_sell)"),
        "mature_large_order_imbalance": ("TradingBehavior", "LargeOrderFlow", "(large_buy-large_sell)/(large_buy+large_sell)"),
        "mature_extra_large_order_imbalance": ("TradingBehavior", "ExtraLargeOrderFlow", "(extra_large_buy-extra_large_sell)/(extra_large_buy+extra_large_sell)"),
        "mature_institutional_order_imbalance": ("TradingBehavior", "InstitutionalFlowProxy", "(large_and_extra_large_buy-sell)/(large_and_extra_large_buy+sell)"),
        "mature_net_flow_to_traded_amount": ("TradingBehavior", "NetFlow", "net_mf_amount_cny/traded_amount_cny"),
        "mature_net_flow_persistence_5": ("TradingBehavior", "NetFlowPersistence", "mean_5(net_flow_to_traded_amount)"),
        "mature_net_flow_persistence_20": ("TradingBehavior", "NetFlowPersistence", "mean_20(net_flow_to_traded_amount)"),
        "mature_institutional_flow_persistence_20": ("TradingBehavior", "InstitutionalFlowPersistence", "mean_20(institutional_order_imbalance)"),
    }
    mf_fields = "buy_sm_amount,sell_sm_amount,buy_md_amount,sell_md_amount,buy_lg_amount,sell_lg_amount,buy_elg_amount,sell_elg_amount,net_mf_amount,traded_amount_cny"
    for name in MONEYFLOW_FACTOR_NAMES:
        family, subfamily, definition = money_specs[name]
        rows.append(_row(name, family, subfamily, definition, "Order-size flow separates retail-like and institution-like trading pressure in A shares.", mf_fields, ("china_order_imbalance",), "factor_universe_v2.mature_factors.compute_moneyflow_factors"))

    fundamental_specs = {
        "mature_gross_profitability": ("Profitability", "GrossProfitability", "(revenue-oper_cost)/total_assets", ("gross_profitability",)),
        "mature_operating_profitability": ("Profitability", "OperatingProfitability", "operate_profit/total_assets", ("gross_profitability", "barra")),
        "mature_return_on_assets": ("Profitability", "ReturnOnAssets", "n_income_attr_p/total_assets", ("barra", "a_share_review")),
        "mature_book_leverage": ("Leverage", "DebtToAssets", "total_liab/total_assets", ("barra",)),
        "mature_current_ratio": ("Quality", "ShortTermSolvency", "total_cur_assets/total_cur_liab", ("barra",)),
        "mature_cash_ratio": ("Quality", "CashSolvency", "money_cap/total_cur_liab", ("barra",)),
        "mature_operating_cashflow_to_assets": ("CashFlow", "CashflowOnAssets", "n_cashflow_act/total_assets", ("accruals", "barra")),
        "mature_cashflow_quality": ("Quality", "CashflowQuality", "n_cashflow_act/abs(n_income_attr_p)", ("accruals", "barra")),
        "mature_accruals_to_assets": ("Quality", "Accruals", "(n_income_attr_p-n_cashflow_act)/total_assets", ("accruals",)),
        "mature_asset_growth_yoy": ("GrowthInvestment", "AssetGrowth", "total_assets/prior_year_total_assets-1", ("barra",)),
        "mature_revenue_growth_yoy": ("GrowthInvestment", "RevenueGrowth", "revenue/prior_year_revenue-1", ("barra",)),
        "mature_net_income_growth_yoy": ("GrowthInvestment", "EarningsGrowth", "signed_yoy_growth(n_income_attr_p)", ("barra",)),
        "mature_cashflow_to_sales": ("CashFlow", "CashConversion", "n_cashflow_act/revenue", ("accruals",)),
        "mature_gross_margin": ("Profitability", "GrossMargin", "(revenue-oper_cost)/revenue", ("gross_profitability", "barra")),
        "mature_net_margin": ("Profitability", "NetMargin", "n_income_attr_p/revenue", ("barra",)),
        "mature_book_to_market_pit": ("Value", "BookToMarketPIT", "PIT_book_equity/market_cap_cny", ("china_size_value", "a_share_review")),
        "mature_earnings_to_price_pit": ("Value", "EarningsYieldPIT", "PIT_net_income/market_cap_cny", ("china_size_value",)),
        "mature_sales_to_price_pit": ("Value", "SalesToPricePIT", "PIT_revenue/market_cap_cny", ("a_share_review", "barra")),
        "mature_cashflow_to_price_pit": ("Value", "CashflowToPricePIT", "PIT_operating_cashflow/market_cap_cny", ("a_share_review", "accruals")),
    }
    fundamental_fields = "information_available_date,revenue,oper_cost,operate_profit,n_income_attr_p,total_assets,total_liab,total_hldr_eqy_exc_min_int,money_cap,total_cur_assets,total_cur_liab,n_cashflow_act,prior_total_assets,prior_revenue,prior_n_income_attr_p,total_mv_cny"
    for name in FUNDAMENTAL_FACTOR_NAMES:
        family, subfamily, definition, source_keys = fundamental_specs[name]
        rows.append(_row(name, family, subfamily, definition, "Mature accounting characteristic computed only from the latest revision available at the decision date.", fundamental_fields, source_keys, "factor_universe_v2.mature_factors.compute_fundamental_factors"))
    frame = pd.DataFrame(rows)
    if len(frame) != 58 or not frame["factor_name"].is_unique:
        raise AssertionError("mature factor inventory must contain 58 unique admitted factors")
    return frame


def build_external_research_inventory() -> pd.DataFrame:
    admitted = build_mature_factor_inventory()
    pending = pd.DataFrame(
        [
            {"factor_name": "alpha191_family", "source": "Alpha191", "source_family": "Alpha191", "source_citations": "public_formula_lists_multiple_unverified_origins", "definition": "191 formulaic price-volume alphas", "economic_rationale": "Broad formula library but overlaps the existing 669 technical core.", "required_fields": "OHLCVA", "economic_family": "Multi", "economic_subfamily": "FormulaLibrary", "secondary_family": "", "pit_implications": "same_day_after_close", "evidence_tier": "C", "implementation_status": "rejected_v2_batch", "compute_adapter": "", "candidate_decision": "reject", "decision_reason": "provenance_license_unclear_and_high_overlap_with_existing_technical_core"},
            {"factor_name": "joinquant_ricequant_factor_libraries", "source": "JoinQuant/RiceQuant", "source_family": "MaturePlatforms", "source_citations": "https://www.joinquant.com/view/factorlib/list", "definition": "public platform factor taxonomies", "economic_rationale": "Useful taxonomy and cross-check source.", "required_fields": "platform_specific", "economic_family": "Multi", "economic_subfamily": "PlatformLibrary", "secondary_family": "", "pit_implications": "definition_specific", "evidence_tier": "B", "implementation_status": "taxonomy_only", "compute_adapter": "", "candidate_decision": "reject", "decision_reason": "no_portable_formula_or_license_proven_for_direct_code_adaptation"},
            {"factor_name": "industry_relative_signals", "source": "MSCI_Barra_and_SW", "source_family": "BarraStyle", "source_citations": SOURCES["barra"], "definition": "industry-relative residualized characteristics", "economic_rationale": "Controls structural industry composition.", "required_fields": "historically_vintaged_industry_membership", "economic_family": "MarketIndustry", "economic_subfamily": "IndustryRelative", "secondary_family": "", "pit_implications": "requires_membership_database_vintage", "evidence_tier": "A", "implementation_status": "research_pending", "compute_adapter": "", "candidate_decision": "defer", "decision_reason": "effective_intervals_do_not_prove_historical_database_vintage"},
            {"factor_name": "forecast_express_surprise", "source": "Tushare", "source_family": "AshareEvents", "source_citations": "https://tushare.pro/document/2?doc_id=45;https://tushare.pro/document/2?doc_id=46", "definition": "announcement surprise relative to prior expectation", "economic_rationale": "Forward-looking earnings news.", "required_fields": "forecast,express,consensus_or_prior_guidance", "economic_family": "GrowthInvestment", "economic_subfamily": "EarningsSurprise", "secondary_family": "", "pit_implications": "announcement_timestamp_and_baseline_required", "evidence_tier": "B", "implementation_status": "research_pending", "compute_adapter": "", "candidate_decision": "defer", "decision_reason": "probe_accessible_but_history_baseline_and_sparse_coverage_not_proven"},
            {"factor_name": "margin_northbound_block_toplist_events", "source": "Tushare", "source_family": "AshareEvents", "source_citations": "https://tushare.pro/document/2?doc_id=58;https://tushare.pro/document/2?doc_id=188", "definition": "margin, northbound, block-trade and abnormal-list signals", "economic_rationale": "China-specific investor and event behavior.", "required_fields": "multiple_sparse_event_APIs", "economic_family": "TradingBehavior", "economic_subfamily": "SparseEvents", "secondary_family": "", "pit_implications": "dataset_specific_next_day_or_after_close", "evidence_tier": "B", "implementation_status": "research_pending", "compute_adapter": "", "candidate_decision": "defer", "decision_reason": "heterogeneous_history_and_sparse_coverage_need_separate_batch"},
            {"factor_name": "price_limit_st_suspension_alpha", "source": "Tushare_and_existing_tradability", "source_family": "AshareMarketStructure", "source_citations": "https://tushare.pro/document/2?doc_id=183", "definition": "limit/ST/suspension state transformed into alpha", "economic_rationale": "Important A-share market structure.", "required_fields": "stk_limit,ST,vintaged_suspension", "economic_family": "MarketIndustry", "economic_subfamily": "TradabilityState", "secondary_family": "", "pit_implications": "known_before_open_or_event_timestamp", "evidence_tier": "B", "implementation_status": "rejected_as_factor", "compute_adapter": "", "candidate_decision": "reject", "decision_reason": "retain_as_tradability_and_risk_controls_not_alpha_features"},
        ]
    )
    return pd.concat([admitted, pending], ignore_index=True)
