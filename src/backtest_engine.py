"""
Backtest Engine — IDX Portfolio Rebalancer
Simulates equal-weight portfolio with periodic rebalancing.

Strategy logic:
  - Day 0   : buy equal 1/3 allocation across 3 stocks (100-share lots)
  - Rebal   : sell over-weight stocks → buy under-weight stocks → restore 33.3%
  - Fees    : buy 0.15 %, sell 0.25 % (includes 0.1 % tax)
  - Lot size: 100 shares (IDX standard)
"""
from __future__ import annotations

import numpy as np
from typing import Any, Dict, List, Optional, Set, Tuple


class BacktestEngine:

    INITIAL_CAPITAL: float = 10_000_000.0
    BUY_FEE:         float = 0.0015   # 0.15 %
    SELL_FEE:        float = 0.0025   # 0.25 % (broker + tax)
    LOT_SIZE:        int   = 100

    def __init__(self, processor) -> None:
        self.processor = processor

    # ── Public: main runner ──────────────────────────────────────
    def run(self, stocks: List[str], period: str) -> Dict[str, Any]:
        """Execute full backtest; return serialisable result dict."""
        all_dates    = self.processor.all_dates
        price_matrix = self.processor.get_price_matrix(stocks)
        rebal_dates  = set(self._rebalance_dates(all_dates, period))

        strategy   = self._simulate(stocks, price_matrix, all_dates, rebal_dates)
        benchmarks = self._benchmarks(stocks, price_matrix, all_dates)
        stats      = self._stats(strategy, benchmarks, stocks)
        corr_data  = self.processor.compute_correlation(stocks)

        return {
            "equity_curve":    strategy["equity_curve"],
            "allocation_hist": strategy["allocation_hist"],
            "rebal_events":    strategy["rebal_events"],
            "benchmarks": {
                k: [{"date": d, "value": v} for d, v in zip(all_dates, vals)]
                for k, vals in benchmarks.items()
            },
            "stats":        stats,
            "correlation":  corr_data,
            "dates":        all_dates,
            "stocks":       stocks,
            "stock_names":  {c: self.processor.stock_data[c]["name"] for c in stocks},
            "period":       period,
        }

    # ── Private: rebalancing date schedule ──────────────────────
    def _rebalance_dates(self, dates: List[str], period: str) -> List[str]:
        if period == "weekly":
            return [dates[i] for i in range(4, len(dates), 5)]
        if period == "biweekly":
            return [dates[i] for i in range(9, len(dates), 10)]
        if period == "monthly":
            last: Dict[str, str] = {}
            for d in dates:
                last[d[:7]] = d          # later overwrites → last day of month
            return sorted(last.values())
        if period == "quarterly":
            last_q: Dict[str, str] = {}
            for d in dates:
                q = (int(d[5:7]) - 1) // 3 + 1
                last_q[f"{d[:4]}-Q{q}"] = d
            return sorted(last_q.values())
        return []

    # ── Private: day-by-day simulation ──────────────────────────
    def _simulate(
        self,
        stocks:       List[str],
        price_matrix: Dict,
        all_dates:    List[str],
        rebal_dates:  Set[str],
    ) -> Dict[str, Any]:

        N     = len(stocks)
        cash  = self.INITIAL_CAPITAL
        holds = {s: 0 for s in stocks}    # shares held per stock
        total_fees = 0.0
        equity_curve:    List[Dict] = []
        allocation_hist: List[Dict] = []
        rebal_events:    List[Dict] = []

        # Initial equal-weight purchase on day 0
        target_each = self.INITIAL_CAPITAL / N
        for s in stocks:
            price = price_matrix[s][0]
            if not price:
                continue
            lots = int(target_each / price / self.LOT_SIZE) * self.LOT_SIZE
            cost = lots * price * (1 + self.BUY_FEE)
            if lots > 0 and cost <= cash:
                holds[s]    = lots
                cash       -= cost
                total_fees += lots * price * self.BUY_FEE

        for i, date in enumerate(all_dates):
            sv = {s: holds[s] * (price_matrix[s][i] or 0.0) for s in stocks}
            pv = cash + sum(sv.values())
            w  = {s: sv[s] / pv if pv > 0 else 1 / N for s in stocks}

            equity_curve.append({"date": date, "value": round(pv, 2)})
            allocation_hist.append({
                "date": date,
                "weights": {s: round(w[s] * 100, 2) for s in stocks},
            })

            if date in rebal_dates and i > 0:
                event, cash, holds, fees = self._rebalance(
                    stocks, price_matrix, i, pv, sv, holds, cash
                )
                total_fees += fees
                if event:
                    rebal_events.append(event)

        last_i = len(all_dates) - 1
        final  = cash + sum(holds[s] * (price_matrix[s][last_i] or 0.0) for s in stocks)

        return {
            "equity_curve":    equity_curve,
            "allocation_hist": allocation_hist,
            "rebal_events":    rebal_events,
            "final_value":     round(final, 2),
            "total_fees":      round(total_fees, 2),
        }

    def _rebalance(
        self,
        stocks, pm, idx, port_value, sv, holds, cash
    ) -> Tuple[Optional[Dict], float, Dict, float]:
        """
        Execute one rebalancing event.
        Returns (event | None, new_cash, new_holds, fees_paid).
        """
        target      = port_value / len(stocks)
        trades: Dict[str, Dict] = {}
        fees_paid   = 0.0

        # ── Step 1: sell over-weight ─────────────────────────────
        for s in stocks:
            price = pm[s][idx]
            if not price or not holds[s]:
                continue
            excess = sv[s] - target
            if excess < price * self.LOT_SIZE:
                continue
            lots = min(int(excess / price / self.LOT_SIZE) * self.LOT_SIZE, holds[s])
            if lots <= 0:
                continue
            rev  = lots * price
            fee  = rev * self.SELL_FEE
            holds[s] -= lots
            cash     += rev - fee
            fees_paid += fee
            trades[s] = {"action": "SELL", "shares": lots,
                         "price": round(price, 2), "value": round(rev, 2), "fee": round(fee, 2)}

        # ── Step 2: buy under-weight ─────────────────────────────
        new_sv  = {s: holds[s] * (pm[s][idx] or 0.0) for s in stocks}
        new_pv  = cash + sum(new_sv.values())
        new_tgt = new_pv / len(stocks)

        for s in stocks:
            if s in trades:
                continue
            price = pm[s][idx]
            if not price:
                continue
            deficit = new_tgt - new_sv[s]
            if deficit < price * self.LOT_SIZE:
                continue
            max_lots = int(cash * 0.95 / (price * (1 + self.BUY_FEE)) / self.LOT_SIZE) * self.LOT_SIZE
            lots     = min(int(deficit / price / self.LOT_SIZE) * self.LOT_SIZE, max_lots)
            cost     = lots * price * (1 + self.BUY_FEE)
            if lots <= 0 or cost > cash:
                continue
            holds[s]  += lots
            cash      -= cost
            fee        = lots * price * self.BUY_FEE
            fees_paid += fee
            trades[s]  = {"action": "BUY", "shares": lots,
                          "price": round(price, 2), "value": round(lots * price, 2), "fee": round(fee, 2)}

        if not trades:
            return None, cash, holds, fees_paid

        final_sv = {s: holds[s] * (pm[s][idx] or 0.0) for s in stocks}
        final_pv = cash + sum(final_sv.values())
        event = {
            "date":               self.processor.all_dates[idx],
            "portfolio_value":    round(port_value, 2),
            "new_portfolio_value": round(final_pv, 2),
            "trades":             trades,
            "weights_after": {
                s: round(final_sv[s] / final_pv * 100, 1) if final_pv > 0 else 33.3
                for s in stocks
            },
            "cash_after": round(cash, 2),
        }
        return event, cash, holds, fees_paid

    # ── Private: benchmarks ──────────────────────────────────────
    def _benchmarks(self, stocks, pm, all_dates) -> Dict[str, List[float]]:
        N     = len(stocks)
        bench = {}

        # Equal-weight buy & hold (no rebalancing)
        cash  = self.INITIAL_CAPITAL
        bh    = {}
        for s in stocks:
            p0 = pm[s][0]
            if not p0:
                bh[s] = 0
                continue
            lots  = int((self.INITIAL_CAPITAL / N) / p0 / self.LOT_SIZE) * self.LOT_SIZE
            bh[s] = lots
            cash -= lots * p0 * (1 + self.BUY_FEE)
        bench["equal_bh"] = [
            round(cash + sum(bh[s] * (pm[s][i] or 0.0) for s in stocks), 2)
            for i in range(len(all_dates))
        ]

        # Per-stock all-in buy & hold
        for s in stocks:
            c  = self.INITIAL_CAPITAL
            p0 = pm[s][0]
            if p0:
                lots = int(self.INITIAL_CAPITAL / p0 / self.LOT_SIZE) * self.LOT_SIZE
                c   -= lots * p0 * (1 + self.BUY_FEE)
                bench[f"bh_{s}"] = [round(c + lots * (pm[s][i] or 0.0), 2) for i in range(len(all_dates))]
            else:
                bench[f"bh_{s}"] = [self.INITIAL_CAPITAL] * len(all_dates)

        return bench

    # ── Private: statistics ──────────────────────────────────────
    def _stats(self, strategy, bench, stocks) -> Dict[str, Any]:
        vals  = [e["value"] for e in strategy["equity_curve"]]
        n     = len(vals)
        final = vals[-1]
        init  = self.INITIAL_CAPITAL

        total_ret  = (final - init) / init * 100
        annual_ret = (pow(final / init, 252 / n) - 1) * 100

        # Max drawdown
        peak = max_dd = 0.0
        dd_curve: List[float] = []
        for v in vals:
            if v > peak:
                peak = v
            dd = (peak - v) / peak * 100
            if dd > max_dd:
                max_dd = dd
            dd_curve.append(round(-dd, 3))

        # Sharpe (daily, rf = 0)
        dr     = np.diff(vals) / np.array(vals[:-1])
        sharpe = float(np.mean(dr) / np.std(dr) * np.sqrt(252)) if np.std(dr) > 0 else 0.0

        bh_ret = (bench["equal_bh"][-1] - init) / init * 100
        excess = total_ret - bh_ret

        indiv = [
            {"code": s, "return": round((bench[f"bh_{s}"][-1] - init) / init * 100, 2)}
            for s in stocks
        ]

        return {
            "total_return":   round(total_ret,  3),
            "annual_return":  round(annual_ret, 3),
            "bh_return":      round(bh_ret,     3),
            "excess_return":  round(excess,     3),
            "max_drawdown":   round(max_dd,     3),
            "sharpe":         round(sharpe,     3),
            "rebal_count":    len(strategy["rebal_events"]),
            "total_fees":     strategy["total_fees"],
            "best_stock":     max(indiv, key=lambda x: x["return"]),
            "worst_stock":    min(indiv, key=lambda x: x["return"]),
            "final_value":    strategy["final_value"],
            "drawdown_curve": dd_curve,
            "indiv_returns":  indiv,
        }
