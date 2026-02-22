"""
Data Processor — IDX Portfolio Rebalancer
Handles CSV ingestion, stock universe filtering, price-matrix
construction, correlation analysis, and uncorrelated-trio selection.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional


class DataProcessor:
    """Load and preprocess IDX daily stock data from a CSV file."""

    def __init__(self, csv_path: str) -> None:
        self.csv_path = csv_path
        # { code: {name: str, rows: [{date, close, volume}]} }
        self.stock_data: Dict[str, Any]    = {}
        self.all_dates:   List[str]        = []   # sorted trading-date strings
        self.all_ranked_stocks: List[Dict] = []   # all eligible stocks sorted by vol
        self.top20_stocks: List[Dict]      = []   # top-20% slice (back-compat)

    # ── Public: load ────────────────────────────────────────────
    def load(self) -> None:
        """Parse CSV, build stock_data dict, all_dates list, and top20 list."""
        df = pd.read_csv(self.csv_path)
        df["date"] = df["Date"].str.split("T").str[0]
        df = df[(df["Close"].notna()) & (df["Close"] > 0)].copy()

        for _, row in df.iterrows():
            code = str(row["StockCode"])
            if code not in self.stock_data:
                self.stock_data[code] = {"name": str(row["StockName"]), "rows": []}
            self.stock_data[code]["rows"].append({
                "date":   row["date"],
                "close":  float(row["Close"]),
                "volume": float(row["Volume"]) if pd.notna(row["Volume"]) else 0.0,
            })

        for code in self.stock_data:
            self.stock_data[code]["rows"].sort(key=lambda r: r["date"])

        self.all_dates = sorted(df["date"].unique().tolist())
        self._compute_ranked_stocks()

    # ── Public: stock list ───────────────────────────────────────
    def get_stocks_by_pct(self, top_pct: float) -> List[Dict]:
        """Return top `top_pct` percent of all eligible stocks by 2025 volume."""
        n = max(1, int(len(self.all_ranked_stocks) * top_pct / 100))
        return self.all_ranked_stocks[:n]

    def get_top20_stocks(self) -> Dict:
        return {
            "stocks":      self.top20_stocks,
            "total_dates": len(self.all_dates),
            "date_range":  {"start": self.all_dates[0], "end": self.all_dates[-1]},
        }

    # ── Public: aligned price matrix ────────────────────────────
    def get_price_matrix(self, stocks: List[str]) -> Dict[str, List[Optional[float]]]:
        """
        Return {code: [price_per_date]} with forward-fill for missing dates.
        Length of each list == len(self.all_dates).
        """
        matrix: Dict[str, List[Optional[float]]] = {}
        for code in stocks:
            price_map: Dict[str, float] = {
                r["date"]: r["close"]
                for r in self.stock_data.get(code, {}).get("rows", [])
                if r["close"] > 0
            }
            last: Optional[float] = None
            arr: List[Optional[float]] = []
            for d in self.all_dates:
                if d in price_map:
                    last = price_map[d]
                arr.append(last)
            matrix[code] = arr
        return matrix

    # ── Public: correlation ──────────────────────────────────────
    def compute_correlation(self, stocks: List[str]) -> Dict:
        """
        Return full Pearson matrix and rolling-20d pairwise series.
        """
        pm   = self.get_price_matrix(stocks)
        rets = self._returns(pm, stocks)

        # Full matrix
        matrix: Dict[str, Dict[str, float]] = {}
        for a in stocks:
            matrix[a] = {}
            for b in stocks:
                matrix[a][b] = (
                    1.0 if a == b
                    else round(float(np.nan_to_num(
                        np.corrcoef(rets[a], rets[b])[0, 1]
                    )), 4)
                )

        # Rolling 20-day
        n_dates = len(self.all_dates)
        rolling: Dict[str, List] = {}
        for i, a in enumerate(stocks):
            for j, b in enumerate(stocks):
                if j <= i:
                    continue
                key    = f"{a}-{b}"
                ra, rb = rets[a], rets[b]
                n      = min(len(ra), len(rb))
                vals: List = [None] * n_dates
                for t in range(20, n):
                    c = np.corrcoef(ra[t-20:t], rb[t-20:t])[0, 1]
                    vals[t + 1] = round(float(np.nan_to_num(c)), 4)
                rolling[key] = vals

        return {"matrix": matrix, "rolling": rolling, "dates": self.all_dates}

    # ── Public: auto-select uncorrelated trio ────────────────────
    def find_uncorrelated_trio(self, n_candidates: int = 60, top_pct: float = 20) -> Dict:
        """
        Greedy algorithm:
          S1 = highest-volume candidate
          S2 = lowest |corr| with S1
          S3 = lowest sum of |corr| with S1 + S2
        """
        universe   = self.get_stocks_by_pct(top_pct)
        candidates = [s["code"] for s in universe[:n_candidates]]
        if len(candidates) < 3:
            return {"error": "Not enough candidate stocks"}

        pm   = self.get_price_matrix(candidates)
        rets = self._returns(pm, candidates)

        s1 = candidates[0]

        s2, best = candidates[1], float("inf")
        for c in candidates[1:]:
            if abs(self._corr(rets[s1], rets[c])) < best:
                best, s2 = abs(self._corr(rets[s1], rets[c])), c

        s3, best = candidates[2], float("inf")
        for c in candidates:
            if c in (s1, s2):
                continue
            score = abs(self._corr(rets[s1], rets[c])) + abs(self._corr(rets[s2], rets[c]))
            if score < best:
                best, s3 = score, c

        trio      = [s1, s2, s3]
        corr_data = self.compute_correlation(trio)

        return {
            "stocks":       trio,
            "names":        {c: self.stock_data[c]["name"] for c in trio},
            "correlations": corr_data["matrix"],
            "vol_ranks": {
                c: next(s["rank"] for s in self.top20_stocks if s["code"] == c)
                for c in trio
            },
        }

    # ── Private helpers ──────────────────────────────────────────
    def _compute_ranked_stocks(self) -> None:
        vol2025: Dict[str, float] = {
            code: sum(r["volume"] for r in data["rows"] if r["date"].startswith("2025"))
            for code, data in self.stock_data.items()
        }
        sorted_stocks = sorted(vol2025.items(), key=lambda x: -x[1])
        min_days = int(len(self.all_dates) * 0.6)

        self.all_ranked_stocks = []
        rank = 0
        for code, vol in sorted_stocks:          # ALL stocks, not just top 20%
            active = [
                r for r in self.stock_data[code]["rows"]
                if r["close"] > 0 and r["volume"] > 0
            ]
            if len(active) < min_days:
                continue
            rank += 1
            self.all_ranked_stocks.append({
                "code":        code,
                "name":        self.stock_data[code]["name"],
                "vol2025":     int(vol),
                "rank":        rank,
                "active_days": len(active),
            })

        top_n = max(1, int(len(self.all_ranked_stocks) * 0.2))
        self.top20_stocks = self.all_ranked_stocks[:top_n]

    @staticmethod
    def _returns(pm: Dict, stocks: List[str]) -> Dict[str, np.ndarray]:
        """Daily return arrays (0.0 where price unavailable)."""
        out: Dict[str, np.ndarray] = {}
        for code in stocks:
            prices = pm[code]
            rets   = []
            for i in range(1, len(prices)):
                p0, p1 = prices[i - 1], prices[i]
                rets.append((p1 - p0) / p0 if p1 and p0 and p0 > 0 else 0.0)
            out[code] = np.array(rets, dtype=float)
        return out

    @staticmethod
    def _corr(a: np.ndarray, b: np.ndarray) -> float:
        n = min(len(a), len(b))
        return float(np.nan_to_num(np.corrcoef(a[:n], b[:n])[0, 1])) if n >= 5 else 0.0
