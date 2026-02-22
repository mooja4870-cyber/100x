from typing import List, Dict
from backend.models.schemas import UserConfig, TradeSetupOutput

class RiskValidator:
    """포지션 진입 전 리스크 규칙 검증 게이트 (Act 지침 반영)"""

    RULES_CONFIG = {
        "min_rr_ratio": 1.5,
        "max_leverage": 125,
        "max_position_pct": 0.30,      # 시드 대비 마진 30% 초과 금지
        "max_concurrent_positions": 3,
        "max_total_risk_pct": 0.05,     # 동시 포지션 합산 리스크 5%
        "min_liq_distance_pct": 2.0,    # 청산가까지 최소 2%
        "sl_buffer_pct": 0.003,         # SL 휩소 방어 0.3%
    }

    def validate(self, calc_result: TradeSetupOutput, config: UserConfig, active_positions: List[Dict]) -> Dict:
        """모든 규칙 검증 → pass/fail + 사유"""
        checks = []

        # R3: 최소 손익비
        rr = calc_result.risk_reward_ratio
        checks.append({
            "rule": "R3_MIN_RR",
            "pass": rr >= self.RULES_CONFIG["min_rr_ratio"],
            "value": rr,
            "threshold": self.RULES_CONFIG["min_rr_ratio"],
            "msg": f"손익비 {rr} < 최소 {self.RULES_CONFIG['min_rr_ratio']}"
                   if rr < self.RULES_CONFIG["min_rr_ratio"] else "OK"
        })

        # R4: 수수료 손익분기 vs TP
        tp_pct = calc_result.tp_pct
        min_pct = calc_result.min_profit_pct
        fee_ok = tp_pct > min_pct
        checks.append({
            "rule": "R4_FEE_BREAKEVEN",
            "pass": fee_ok,
            "value": tp_pct,
            "threshold": min_pct,
            "msg": f"TP({tp_pct}%) < 수수료 손익분기({min_pct}%)" if not fee_ok else "OK"
        })

        # R5: 동시 포지션 수
        pos_count = len(active_positions) + 1
        checks.append({
            "rule": "R5_MAX_POSITIONS",
            "pass": pos_count <= self.RULES_CONFIG["max_concurrent_positions"],
            "value": pos_count,
            "threshold": self.RULES_CONFIG["max_concurrent_positions"],
            "msg": f"동시 포지션 {pos_count}개 > 최대 {self.RULES_CONFIG['max_concurrent_positions']}개"
                   if pos_count > self.RULES_CONFIG["max_concurrent_positions"] else "OK"
        })

        # R6: 청산 안전거리
        entry = calc_result.entry_price
        liq = calc_result.estimated_liq_price
        liq_dist = abs(entry - liq) / entry * 100
        checks.append({
            "rule": "R6_LIQ_SAFETY",
            "pass": liq_dist >= self.RULES_CONFIG["min_liq_distance_pct"],
            "value": round(liq_dist, 2),
            "threshold": self.RULES_CONFIG["min_liq_distance_pct"],
            "msg": f"청산거리 {liq_dist:.2f}% < 최소 {self.RULES_CONFIG['min_liq_distance_pct']}%"
                   if liq_dist < self.RULES_CONFIG["min_liq_distance_pct"] else "OK"
        })

        # R7: 마진 비율
        margin_required = (calc_result.quantity * calc_result.entry_price) / calc_result.leverage
        margin_pct = margin_required / config.account_balance
        checks.append({
            "rule": "R7_MARGIN_PCT",
            "pass": margin_pct <= self.RULES_CONFIG["max_position_pct"],
            "value": round(margin_pct * 100, 2),
            "threshold": self.RULES_CONFIG["max_position_pct"] * 100,
            "msg": f"마진 비율 {margin_pct*100:.2f}% > 최대 {self.RULES_CONFIG['max_position_pct']*100}%"
                   if margin_pct > self.RULES_CONFIG["max_position_pct"] else "OK"
        })

        all_pass = all(c["pass"] for c in checks)
        failed = [c for c in checks if not c["pass"]]

        return {
            "approved": all_pass,
            "checks": checks,
            "failed_rules": failed,
            "summary": "✅ 진입 승인" if all_pass 
                       else f"❌ 진입 차단: {', '.join(c['rule'] for c in failed)}"
        }
