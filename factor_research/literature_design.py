"""Explicit, outcome-blind semantic decisions for the frozen 494 identities.

Unknown Alpha101 semantics are disclosed raw carry-through, never inferred signs.
The mappings below describe measured states, not expected-return directions.
"""
from __future__ import annotations

from collections import defaultdict
import re

from factor_research.literature_representation import bucket, digest, grid_center, validate_recipe

# Explicit review of current U identities, not a rule to admit future hold rows.
U_AUDIT = {
    'ta_momentum_ao': 'difference of 5/34 median-price means; provider price scale remains unresolved',
    'ta_momentum_kama': 'causal adaptive price average; accepted canonical state anchor retained; provider scale unresolved',
    'ta_trend_adx_neg': 'negative directional movement ratio; recursive coverage limitation retained, no state repair',
    'ta_trend_adx_pos': 'positive directional movement ratio; recursive coverage limitation retained, no state repair',
    'ta_trend_ema_fast': '12-period recursive price mean; source warmup and provider scale retained',
    'ta_trend_ema_slow': '26-period recursive price mean; source warmup and provider scale retained',
    'ta_trend_sma_fast': '12-period rolling price mean; provider scale unresolved',
    'ta_trend_sma_slow': '26-period rolling price mean; provider scale unresolved',
    'ta_trend_ichimoku_a': 'mean of conversion/base lines; visual=False, no forward chart shift; raw price scale',
    'ta_trend_ichimoku_b': '52-period high-low midpoint; visual=False, raw price scale',
    'ta_trend_ichimoku_base': '26-period high-low midpoint; visual=False, raw price scale',
    'ta_trend_ichimoku_conv': '9-period high-low midpoint; visual=False, raw price scale',
    'ta_trend_macd': 'fast-minus-slow recursive price means; absolute price difference, not PPO',
    'ta_trend_macd_signal': 'recursive mean of MACD price difference; not a percentage oscillator',
    'ta_trend_macd_diff': 'MACD minus its signal; absolute provider price difference',
    'ta_trend_psar_down': 'down-state-only stop price; NaN outside down state is structural and price scale also unresolved',
    'ta_volatility_atr': 'recursive absolute true range in provider price units; both state coverage and scale unresolved',
    'ta_volatility_bbh': '20-period mean plus two price standard deviations; raw band price',
    'ta_volatility_bbm': '20-period mean price, raw band center',
    'ta_volatility_bbhi': 'binary close-above-upper-band; zero is a state, not missing; no jitter/rank',
    'ta_volatility_dch': '20-period rolling high maximum with offset=0; raw price',
    'ta_volatility_dcl': '20-period rolling low minimum with offset=0; raw price',
    'ta_volatility_dcm': 'midpoint of 20-period high/low extremes with offset=0; raw price',
    'ta_volatility_kcc': 'original Keltner typical-price mean, 10-period; raw price',
    'ta_volatility_kch': 'original Keltner upper price channel; no ATR-version substitution',
    'ta_volatility_kcl': 'original Keltner lower price channel; no ATR-version substitution',
    'ta_volatility_kchi': 'binary close-above-original-Keltner-upper-channel; zero retained as state',
    'ta_volume_fi': 'smoothed price-change times volume; units include provider price scale',
    'ta_volume_vwap': '14-period typical-price volume-weighted level; not canonical direct daily vwap',
}
U_ALPHA_IDS = {3,4,5,6,7,11,12,13,14,15,16,24,26,35,40,41,42,44,45,50,55,71,77,83,84,88,94}
U_ALPHA_NAMES = {f'kunquant_alpha101_alpha{n:03d}' for n in U_ALPHA_IDS} | {
    f'kunquant_alpha101_alpha{n:03d}_canonical_vwap_v2' for n in [11,42,50,84,94]}

# mechanism: (theme, common measurement axis, direction, high-value interpretation)
AXES = {
    'normalized_price_slope': ('return_trend', 'normalized_price_slope', 1, 'steeper historical price slope'),
    'alpha158_cntd': ('return_trend', 'up_day_balance', 1, 'larger up-minus-down day share'),
    'alpha158_cntp': ('return_trend', 'up_day_balance', 1, 'larger up-day share'),
    'alpha158_cord': ('trading_activity', 'return_volume_growth_correlation', 1, 'higher return-volume growth correlation'),
    'alpha158_corr': ('trading_activity', 'price_log_volume_correlation', 1, 'higher price-log-volume correlation'),
    'alpha158_imax': ('price_path', 'maximum_position', 1, 'later first maximum within oldest-to-newest window; one-based argmax divided by window'),
    'alpha158_imin': ('price_path', 'minimum_position', 1, 'later first minimum within oldest-to-newest window; one-based argmin divided by window'),
    'alpha158_imxd': ('price_path', 'extrema_position_difference', 1, 'larger normalized IdxMax-minus-IdxMin'),
    'alpha158_ma': ('price_path', 'mean_price_relative_to_current', 1, 'higher historical mean relative to current close'),
    'alpha158_max': ('price_path', 'maximum_relative_to_current', 1, 'higher rolling high maximum relative to current close'),
    'alpha158_min': ('price_path', 'minimum_relative_to_current', 1, 'higher rolling low minimum relative to current close'),
    'alpha158_qtld': ('price_path', 'lower_quantile_relative_to_current', 1, 'higher lower price quantile relative to current close'),
    'alpha158_qtlu': ('price_path', 'upper_quantile_relative_to_current', 1, 'higher upper price quantile relative to current close'),
    'alpha158_rank': ('price_path', 'current_time_series_rank', 1, 'higher current close rank in historical window'),
    'alpha158_resi': ('price_path', 'normalized_regression_residual', 1, 'higher current normalized price regression residual'),
    'alpha158_roc': ('return_trend', 'past_return', -1, 'stronger past close-to-close increase'),
    'alpha158_rsv': ('price_path', 'close_range_position', 1, 'higher close within rolling high-low range'),
    'alpha158_std': ('volatility', 'price_dispersion', 1, 'larger price standard deviation relative to current close'),
    'alpha158_sumd': ('return_trend', 'positive_price_variation', 1, 'greater positive price-change balance'),
    'alpha158_sumn': ('return_trend', 'positive_price_variation', -1, 'smaller negative price-change fraction'),
    'alpha158_sump': ('return_trend', 'positive_price_variation', 1, 'larger positive price-change fraction'),
    'alpha158_vsumd': ('trading_activity', 'positive_volume_variation', 1, 'greater positive volume-change balance'),
    'alpha158_vsumn': ('trading_activity', 'positive_volume_variation', -1, 'smaller negative volume-change fraction'),
    'alpha158_vsump': ('trading_activity', 'positive_volume_variation', 1, 'larger positive volume-change fraction'),
    'intraday_klen': ('within_day_shape', 'intraday_range_open_normalized', 1, 'larger high-low range relative to open'),
    'intraday_klow': ('within_day_shape', 'lower_shadow', 1, 'larger lower candle shadow relative to open'),
    'intraday_kup': ('within_day_shape', 'upper_shadow', 1, 'larger upper candle shadow relative to open'),
    'amount_cv': ('trading_activity', 'amount_relative_variability', 1, 'higher amount coefficient of variation'),
    'amount_mean': ('trading_activity', 'amount_level', 1, 'higher mean traded amount in provider units'),
    'amount_std': ('trading_activity', 'amount_absolute_variability', 1, 'higher amount standard deviation in provider units'),
    'amplitude': ('volatility', 'range_intensity', 1, 'higher average daily high-low amplitude'),
    'corr_ret_amount': ('trading_activity', 'return_amount_level_correlation', 1, 'higher return-amount correlation'),
    'corr_ret_volume': ('trading_activity', 'return_volume_level_correlation', 1, 'higher return-volume correlation'),
    'ret': ('return_trend', 'past_return', 1, 'stronger past close-to-close increase'),
    'rev': ('return_trend', 'past_return', -1, 'stronger past close-to-close increase; undo source reversal sign'),
    'rev_20_exclude_5': ('return_trend', 'past_return_excluding_recent', -1, 'stronger close increase between lag 20 and lag 5'),
    'std': ('volatility', 'return_volatility', 1, 'higher daily-return standard deviation'),
    'mature_amihud_illiquidity': ('liquidity_cost', 'amihud_cost', 1, 'higher absolute return per traded CNY'),
    'mature_book_to_market_pit': ('valuation', 'book_value_latest_statement', 1, 'more latest-available book equity per market value'),
    'mature_book_to_price': ('valuation', 'book_value_vendor_daily', 1, 'higher reciprocal positive vendor pb'),
    'mature_dividend_yield_ttm': ('valuation', 'dividend_yield_vendor_ttm', 1, 'higher vendor trailing dividend yield'),
    'mature_downside_volatility': ('volatility', 'downside_return_volatility', 1, 'higher standard deviation conditional on negative returns'),
    'mature_earnings_to_price_pit': ('valuation', 'earnings_latest_statement', 1, 'more latest-available statement net income per market value'),
    'mature_earnings_yield_ttm': ('valuation', 'earnings_vendor_ttm', 1, 'higher reciprocal positive vendor pe_ttm'),
    'mature_idiosyncratic_volatility': ('residual_risk', 'idiosyncratic_volatility', 1, 'higher rolling estimated market-residual volatility'),
    'mature_intraday_return': ('within_day_shape', 'intraday_return_mean', 1, 'higher mean close/open minus one'),
    'mature_log_total_market_cap': ('size_conditioning', 'size', 1, 'larger vendor total market capitalization'),
    'mature_max_daily_return': ('asymmetry', 'maximum_daily_return', 1, 'larger extreme positive daily return'),
    'mature_parkinson_volatility': ('volatility', 'range_intensity', 1, 'higher Parkinson high-low volatility'),
    'mature_realized_volatility': ('volatility', 'return_volatility', 1, 'higher daily-return standard deviation'),
    'mature_return_skewness': ('asymmetry', 'return_skewness', 1, 'more positive daily-return skewness'),
    'mature_reversal_1m': ('return_trend', 'past_return', -1, 'stronger past 21-session increase; undo source reversal sign'),
    'mature_sales_to_price_pit': ('valuation', 'sales_latest_statement', 1, 'more latest-available statement revenue per market value'),
    'mature_sales_to_price_ttm': ('valuation', 'sales_vendor_ttm', 1, 'higher reciprocal positive vendor ps_ttm'),
    'mature_turnover_mean': ('trading_activity', 'turnover_mean', 1, 'higher mean free-float turnover'),
    'mature_turnover_rate_free_float': ('trading_activity', 'turnover_current', 1, 'higher current free-float turnover'),
    'mature_turnover_volatility': ('trading_activity', 'turnover_variability', 1, 'higher turnover standard deviation'),
    'mature_vwap_deviation': ('price_path', 'close_vwap_deviation', 1, 'higher average close relative to direct vwap'),
}

TA_AXES = {
    'KSTIndicator.kst': ('return_trend', 'kst', 'higher weighted sum of four smoothed rate-of-change measurements'),
    'KSTIndicator.kst_sig': ('return_trend', 'kst_signal', 'higher rolling mean of the KST measurement'),
    'KSTIndicator.kst_diff': ('return_trend', 'kst_difference', 'higher KST relative to its rolling signal'),
    'AroonIndicator.aroon_down': ('technical_state', 'aroon_down', 'higher downtrend Aroon statistic'),
    'AroonIndicator.aroon_indicator': ('technical_state', 'aroon_balance', 'higher Aroon up-minus-down'),
    'AroonIndicator.aroon_up': ('technical_state', 'aroon_up', 'higher uptrend Aroon statistic'),
    'BollingerBands.bollinger_pband': ('price_path', 'bollinger_position', 'higher position within Bollinger bands'),
    'CCIIndicator.cci': ('technical_state', 'cci', 'higher typical-price standardized deviation'),
    'ChaikinMoneyFlowIndicator.chaikin_money_flow': ('trading_activity', 'chaikin_flow', 'higher close-location weighted money-flow ratio'),
    'DonchianChannel.donchian_channel_pband': ('price_path', 'donchian_position', 'higher close position within Donchian channel'),
    'DonchianChannel.donchian_channel_wband': ('volatility', 'donchian_width', 'wider relative Donchian channel'),
    'KeltnerChannel.keltner_channel_wband': ('volatility', 'keltner_width', 'wider relative Keltner channel'),
    'MFIIndicator.money_flow_index': ('technical_state', 'mfi', 'higher positive-to-negative money flow oscillator'),
    'MassIndex.mass_index': ('technical_state', 'mass_index', 'higher summed range EMA ratio'),
    'PercentagePriceOscillator.ppo': ('return_trend', 'ppo', 'higher fast-minus-slow percentage price oscillator'),
    'PercentagePriceOscillator.ppo_hist': ('return_trend', 'ppo_hist', 'higher PPO relative to its signal line'),
    'PercentagePriceOscillator.ppo_signal': ('return_trend', 'ppo_signal', 'higher smoothed PPO signal'),
    'PercentageVolumeOscillator.pvo': ('trading_activity', 'pvo', 'higher fast-minus-slow percentage volume oscillator'),
    'PercentageVolumeOscillator.pvo_signal': ('trading_activity', 'pvo_signal', 'higher smoothed volume oscillator'),
    'ROCIndicator.roc': ('return_trend', 'past_return', 'stronger past price increase in percentage units'),
    'RSIIndicator.rsi': ('technical_state', 'rsi', 'higher smoothed upward-versus-downward movement ratio'),
    'STCIndicator.stc': ('technical_state', 'stc', 'higher stochastic-normalized trend cycle state'),
    'TRIXIndicator.trix': ('return_trend', 'trix', 'higher percentage change of triple-smoothed price'),
    'TSIIndicator.tsi': ('technical_state', 'tsi', 'higher double-smoothed signed change relative to absolute change'),
    'UltimateOscillator.ultimate_oscillator': ('technical_state', 'ultimate_oscillator', 'higher weighted buying-pressure ratio'),
    'VortexIndicator.vortex_indicator_diff': ('technical_state', 'vortex_balance', 'higher positive-minus-negative vortex movement'),
    'VortexIndicator.vortex_indicator_neg': ('technical_state', 'vortex_negative', 'higher negative vortex movement'),
    'VortexIndicator.vortex_indicator_pos': ('technical_state', 'vortex_positive', 'higher positive vortex movement'),
}


def dense_identity(row):
    """Only the actual Alpha360 grid, including its canonical Alpha158 aliases."""
    name = row['factor']
    if not name.startswith('alpha360_') and name not in {
            'alpha158_LOW0', 'alpha158_ROC5', 'alpha158_ROC10', 'alpha158_ROC20', 'alpha158_ROC30'}:
        return None
    expression = row['definition'].split(': ', 1)[-1].removesuffix(' Alpha360 batch V4 passed.').replace(' ', '')
    match = re.fullmatch(r'Ref\(\$(close|high|low|open|vwap),(\d+)\)/\$close', expression)
    if match:
        field, lag = match[1], int(match[2])
    elif expression == '$low/$close':
        field, lag = 'low', 0
    else:
        raise ValueError(f'unreviewed dense formula: {name} {expression}')
    return field, lag


def annotate(row):
    out = dict(row)
    name, mechanism = row['factor'], row['mechanism']
    hold = row['replacement_hold_reason']
    dense = dense_identity(row)
    out.update(expected_return_direction='not_asserted_no_outcome_direction_used',
        correctness_status='no_new_correctness_evidence_in_metadata_review',
        statistical_substitution='none_authorized_by_v0_5_1_0_995_proposals',
        semantic_audit_basis='existing_v0_5_1_formula_and_canonical_lineage; new_measurement_axis_review',
        dense_field='', dense_lag='', horizon_type='source_parameter_tuple',
        denominator_reference=row['definition'], direction_evidence='canonical_formula_measurement_axis_not_return_claim')
    if hold:
        if name not in U_AUDIT and name not in U_ALPHA_NAMES:
            raise ValueError(f'unreviewed U identity: {name}')
        reasons = {
            'unresolved_semantics': 'retain canonical audited raw identity; formula interpretation unresolved; no aggregation or sign assertion',
            'provider_price_scale_unverified': 'retain original provider-unit raw value; no ranking/normalization across unresolved stock-specific scales',
            'recursive_missingness_quality_review': 'retain existing causal raw and missing mask; no fill/restart or claimed quality repair',
            'state_or_event_mask_review': 'retain state/event raw mask; do not equate absence of state with missing observation',
        }
        if hold not in reasons:
            raise ValueError(f'unreviewed hold reason: {hold}')
        out.update(economic_theme='unresolved' if hold == 'unresolved_semantics' else 'technical_state',
            subtheme=mechanism, measurement_family=mechanism, measurement_orientation='not_applied_raw_carry_through',
            representation_sign=None, disposition='U_RAW', role_reason=reasons[hold],
            direction_evidence='raw_unchanged_no_direction_required', composite_group='')
        out['u_item_review'] = U_AUDIT.get(name,
            'canonical Alpha101 identity/dated PIT lineage checked; interpretable economic axis remains unresolved; raw-only proposal, not semantic clearance')
        out['u_review_status'] = ('BLOCKED_SEMANTIC_INTERPRETATION_RAW_RETENTION_PROPOSED'
            if name in U_ALPHA_NAMES else 'RAW_RETENTION_PROPOSED_WITH_DISCLOSED_LIMITATION')
    else:
        if dense:
            field, lag = dense
            theme, axis, sign, meaning = 'price_path', f'{field}_relative_to_current_close', 1, f'higher historical {field} relative to current close'
            horizon = bucket(lag)
            out.update(dense_field=field, dense_lag=lag, horizon_type='point_lag', denominator_reference='current canonical close')
        else:
            if mechanism in AXES:
                theme, axis, sign, meaning = AXES[mechanism]
            elif mechanism in TA_AXES:
                theme, axis, meaning = TA_AXES[mechanism]
                sign = 1
            else:
                raise ValueError(f'measurement axis needs human review: {name} {mechanism}')
            horizon = row['horizon']
            # Only two explicitly reviewed cross-library groups share a horizon token.
            if mechanism in {'amplitude', 'mature_parkinson_volatility'}:
                horizon = 'window_20_distinct_estimators_and_min_observations'
            if mechanism in {'ret', 'rev'}:
                horizon = row['horizon']
            out['horizon_type'] = ('accounting_event' if '_pit' in name or '_ttm' in name else
                'interval_return' if mechanism in {'ret', 'rev', 'mature_reversal_1m', 'rev_20_exclude_5', 'alpha158_roc'} else
                'rolling_or_recursive_parameters')
        family = mechanism
        if dense:
            family = f'historical_{dense[0]}_current_close_ratio'
        elif mechanism in {'alpha158_sump', 'alpha158_sumn', 'alpha158_sumd'}:
            family = 'price_change_positive_negative_partition'
        elif mechanism in {'alpha158_vsump', 'alpha158_vsumn', 'alpha158_vsumd'}:
            family = 'volume_change_positive_negative_partition'
        elif mechanism in {'ret', 'rev'}:
            family = 'simple_close_to_close_return'
        out.update(economic_theme=theme, subtheme=axis, measurement_family=family,
            measurement_orientation=meaning, representation_sign=sign, disposition='G_REPRESENTABLE',
            role_reason='measured_axis_is_defined; preserve source horizon/input/mask; no expected-return assertion',
            composite_group=axis+'__'+horizon)
        out.update(u_item_review='not_U_measurement_axis_defined', u_review_status='not_applicable')
    if '_pit' in name:
        availability = 'practical_reconstructed_statement_PIT; information_available_date<=signal; latest statement period not TTM'
    elif '_ttm' in name or mechanism in {'mature_book_to_price', 'mature_log_total_market_cap', 'mature_turnover_rate_free_float'}:
        availability = 'canonical dated daily_basic asof; vendor field/update semantics retained; no rebuilding/forward fill'
    elif row['source'] == 'alpha101':
        availability = 'canonical dated PIT eligibility inside ranks; stable membership axis; canonical direct/proxy vwap identity retained'
    elif name == 'ta_momentum_kama':
        availability = 'causal KAMA state anchor 2000-01-04; missing output preserves state; use stored canonical feature only'
    else:
        availability = 'canonical dated universe and historical/current OHLCV through signal close; exact source warmup/mask retained'
    out['dated_availability_semantics'] = availability
    return out


def build_recipe(semantics, aliases, source_hashes):
    rows = [annotate(r) for r in sorted(semantics, key=lambda x: x['factor'])]
    names = [r['factor'] for r in rows]
    if len(names) != 494 or len(set(names)) != 494:
        raise ValueError('expected frozen 494 identities')
    amap = {r['factor']: r['canonical_representation_proposal'] for r in aliases}
    table = {r['factor']: r for r in rows}
    for row in rows:
        canonical = amap.get(row['factor'], row['factor'])
        row['exact_alias'] = canonical
        if canonical != row['factor']:
            if dense_identity(row) != dense_identity(table[canonical]):
                raise ValueError('alias formula/dense identity mismatch')
            row['disposition'] = 'EXACT_ALIAS_OF'
            row['role_reason'] = 'existing 168-month same-value same-mask equality; retained identity; counted once'
    unique = [r for r in rows if r['exact_alias'] == r['factor']]
    u = sorted(r['factor'] for r in unique if r['disposition'] == 'U_RAW')
    groups = defaultdict(list)
    representatives = []
    for row in unique:
        if row['disposition'] == 'G_REPRESENTABLE':
            groups[row['composite_group']].append(row)
    composites = []
    dense_stats = []
    for key, group in sorted(groups.items()):
        families = defaultdict(list)
        for row in group:
            families[row['measurement_family']].append({'factor': row['factor'], 'sign': row['representation_sign']})
        output = 'erc_' + digest(key)[:16]
        composites.append(dict(id=output, semantic_id=key, economic_theme=group[0]['economic_theme'],
            axis=group[0]['subtheme'], type='rank_singleton' if len(group) == 1 else 'rank_composite',
            families=[dict(id=f, members=sorted(m, key=lambda x: x['factor'])) for f, m in sorted(families.items())]))
        if group[0]['dense_field']:
            center = grid_center([r['dense_lag'] for r in group])
            rep = next(r['factor'] for r in group if r['dense_lag'] == center)
            representatives.append(rep)
            dense_stats.append(dict(group=key, unique_lags=len(group), lags=sorted(r['dense_lag'] for r in group),
                representative=rep, retained_lag=center, composite=output, lost_point_resolution=len(group)-1))
        else:
            # V0.5.1 reports zero qualifying approximate substitutions. Do not invent new pruning.
            representatives.extend(r['factor'] for r in group)
        for row in group:
            row['c_output'] = output
    representatives = sorted(representatives)
    recipe = dict(scope='D1_feature_only_candidate', status='diagnostic_candidate_not_ready_for_human_freeze',
        d2_authorized=False, outcomes_authorized=False, recent_authorized=False,
        discovery_scope='retrospective_development_2010_2023',
        diagnostic_policy=dict(rank_min=100, child_fraction=.5, policy_finalized=False, ties='average'),
        source_hashes=source_hashes, parents=sorted(r['factor'] for r in unique),
        u=u, representatives=representatives, composites=composites)
    c = [x['id'] for x in composites]
    recipe['arms'] = {'R': sorted(u+representatives), 'C': sorted(u+c), 'H': sorted(u+representatives+c)}
    for row in rows:
        canonical = table[row['exact_alias']]
        row['c_output'] = canonical.get('c_output', canonical['factor'])
        row['r_role'] = 'raw' if canonical['factor'] in recipe['arms']['R'] else 'dense_lag_thinned'
        row['c_role'] = 'raw_U' if canonical['factor'] in u else 'rank_constituent'
        row['h_role'] = 'raw_and_rank' if canonical['factor'] in representatives else row['c_role']
    validate_recipe(recipe)
    return rows, recipe, dense_stats
