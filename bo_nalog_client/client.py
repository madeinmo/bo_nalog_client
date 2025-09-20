from __future__ import annotations

import httpx
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Iterable, Optional, Tuple, Union

Number = Optional[float]
Json = Union[Dict[str, Any], Iterable[Dict[str, Any]]]


_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://bo.nalog.gov.ru/",
}


@dataclass
class NalogClient:
    """
    Async client for bo.nalog.gov.ru BFO endpoints.

    Usage:
        async with NalogClient() as nc:
            year, revenue, profit = await nc.get_last_year_revenue_profit(9392519)

    If you already have an AsyncClient you'd like to reuse:

        async with httpx.AsyncClient(headers=_DEFAULT_HEADERS, timeout=20.0) as hc:
            async with NalogClient(client=hc) as nc:
                ...

    Public methods:
        - fetch_bfo(org_id): returns raw JSON for the organization's BFO
        - extract_last_year_revenue_profit(payload, prefer_bfo_date=False)
        - get_last_year_revenue_profit(org_id, prefer_bfo_date=False)
    """
    base_url: str = "https://bo.nalog.gov.ru"
    client: Optional[httpx.AsyncClient] = None
    timeout: float = 20.0

    def __post_init__(self) -> None:
        self._own_client = False
        if self.client is None:
            self.client = httpx.AsyncClient(
                headers=_DEFAULT_HEADERS.copy(),
                timeout=self.timeout,
                http2=True,
            )
            self._own_client = True
        else:
            # Ensure required headers are present without clobbering the user's
            # existing ones.
            for k, v in _DEFAULT_HEADERS.items():
                self.client.headers.setdefault(k, v)

    async def __aenter__(self) -> "NalogClient":
        # httpx.AsyncClient is already async-context compatible, but if we created
        # it ourselves we'll enter it here to ensure connection pooling is ready.
        if self._own_client:
            await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._own_client:
            await self.client.__aexit__(exc_type, exc, tb)

    async def aclose(self) -> None:
        """Manually close if not using `async with`."""
        if self.client is not None and not self.client.is_closed:
            await self.client.aclose()

    # ---------- HTTP ----------

    async def fetch_bfo(self, org_id: Union[int, str]) -> Iterable[Dict[str, Any]]:
        """
        Fetch the BFO list for a given organization ID.

        Returns: iterable of report dicts.
        Raises: httpx.HTTPStatusError on non-2xx responses.
        """
        url = f"{self.base_url}/nbo/organizations/{org_id}/bfo/"
        resp = await self.client.get(url)
        resp.raise_for_status()
        data: Json = resp.json()
        # The API is expected to return a list of reports; normalize if needed.
        if isinstance(data, dict):
            # Some endpoints wrap the list; try common keys, else wrap single dict.
            for key in ("items", "results", "reports", "data"):
                if key in data and isinstance(data[key], list):
                    return data[key]
            return [data]
        return list(data)

    # ---------- Parsing helpers (merged from your snippet) ----------

    @staticmethod
    def _to_num(v: Any) -> Number:
        """Cast '', None -> None; numeric strings -> float; ints/floats -> float."""
        if v in ("", None):
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                return None
        return None

    @staticmethod
    def _to_date(s: Optional[str]) -> Optional[date]:
        if not s:
            return None
        try:
            y, m, d = map(int, s.split("-"))
            return date(y, m, d)
        except Exception:
            return None

    @staticmethod
    def _best_correction(type_corrections: Iterable[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Pick the correction with the highest correctionVersion if present,
        otherwise the first one.
        """
        best = None
        best_ver = -1
        for tc in type_corrections or []:
            corr = (tc or {}).get("correction")
            if not corr:
                continue
            ver = corr.get("correctionVersion")
            if isinstance(ver, int) and ver >= best_ver:
                best_ver = ver
                best = corr
            elif best is None:
                best = corr
        return best

    @classmethod
    def _latest_report(
        cls,
        reports: Iterable[Dict[str, Any]],
        *,
        prefer_bfo_date: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Choose the latest report.
        - Default: by numeric 'period' (e.g., "2024").
        - If prefer_bfo_date=True: by 'actualBfoDate' (ties broken by period).
        """
        def key_by_period(r: Dict[str, Any]):
            try:
                return int(str(r.get("period", 0)))
            except Exception:
                return -10**9

        def key_by_bfo(r: Dict[str, Any]):
            return (cls._to_date(r.get("actualBfoDate")) or date.min, key_by_period(r))

        reps = list(reports or [])
        if not reps:
            return None
        return max(reps, key=key_by_bfo if prefer_bfo_date else key_by_period)

    @classmethod
    def extract_last_year_revenue_profit(
        cls,
        payload: Iterable[Dict[str, Any]],
        *,
        prefer_bfo_date: bool = False
    ) -> Optional[Tuple[int, Number, Number]]:
        """
        Returns (year, revenue_2110, net_profit_2400) for the 'latest' report.
        - Revenue: financialResult['current2110']
        - Net Profit (loss): financialResult['current2400']
        """
        rpt = cls._latest_report(payload, prefer_bfo_date=prefer_bfo_date)
        if not rpt:
            return None

        year = int(str(rpt.get("period", "0")))
        corr = cls._best_correction(rpt.get("typeCorrections", []))
        if not corr:
            return (year, None, None)

        fr = corr.get("financialResult", {}) or {}
        revenue = cls._to_num(fr.get("current2110"))
        profit = cls._to_num(fr.get("current2400"))
        return year, revenue, profit

    # ---------- Convenience combo ----------

    async def get_last_year_revenue_profit(
        self,
        org_id: Union[int, str],
        *,
        prefer_bfo_date: bool = False
    ) -> Optional[Tuple[int, Number, Number]]:
        """
        Fetch BFO for org_id and return (year, revenue_2110, net_profit_2400)
        for the latest report.
        """
        payload = await self.fetch_bfo(org_id)
        return self.extract_last_year_revenue_profit(payload, prefer_bfo_date=prefer_bfo_date)
