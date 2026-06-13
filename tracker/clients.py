"""Two clients:

  Travelpayouts (Aviasales Data API)  -> CACHED prices, free, used for the broad month scan.
  SerpApi Google Flights             -> LIVE prices, gated, used only to confirm candidates.
"""
from __future__ import annotations

import certifi
import httpx

# certifi CA bundle: makes TLS verification work on machines (e.g. macOS Python)
# whose default trust store httpx can't find. Harmless on Linux CI.
CA_BUNDLE = certifi.where()

# ---------------------------------------------------------------------------
# Travelpayouts – cached "month matrix" (one call returns a whole month)
# ---------------------------------------------------------------------------
# The /v1/prices/calendar endpoint ignores the requested month and returns a
# generic cheapest-tickets blob. /v2/prices/month-matrix is the one that returns
# the cheapest cached fare *per departure day* for a given month. It only serves
# ONE-WAY records (one_way=false comes back empty), so we fetch each direction
# separately and build round trips as "split" fares in analyze.py.
#   docs: https://support.travelpayouts.com/  ->  Data API  ->  Calendar of prices for a month
TP_MONTH_MATRIX_URL = "https://api.travelpayouts.com/v2/prices/month-matrix"


class Travelpayouts:
    def __init__(self, token: str, currency: str, timeout: int = 30) -> None:
        self.token = token
        self.currency = currency
        self.timeout = timeout

    async def one_way_calendar(
        self,
        client: httpx.AsyncClient,
        origin: str,
        destination: str,
        month: str,            # "YYYY-MM"
    ) -> dict[str, float]:
        """Return {depart_date: cheapest_one_way_price} for each cached day of `month`.

        The cache is sparse and only reaches a few months out, so far-future
        months (and thin routes) legitimately come back empty.
        """
        params = {
            "origin": origin,
            "destination": destination,
            "month": f"{month}-01",        # endpoint wants the first day of the month
            "currency": self.currency,
            "show_to_affiliates": "true",
            "one_way": "true",
            "token": self.token,
        }
        resp = await client.get(TP_MONTH_MATRIX_URL, params=params, timeout=self.timeout)
        resp.raise_for_status()
        payload = resp.json()

        out: dict[str, float] = {}
        for rec in payload.get("data") or []:
            day = rec.get("depart_date")
            price = rec.get("value")
            if not day or price is None:
                continue
            price = float(price)
            # Keep the cheapest record per day (the API usually pre-dedupes, but be safe).
            if day not in out or price < out[day]:
                out[day] = price
        return out


# ---------------------------------------------------------------------------
# SerpApi Google Flights – live, accurate (covers IndiGo/Air India/Akasa/SpiceJet)
# ---------------------------------------------------------------------------
SERPAPI_URL = "https://serpapi.com/search"


class SerpApi:
    def __init__(self, api_key: str, currency: str = "INR") -> None:
        self.api_key = api_key
        self.currency = currency

    def price(
        self,
        departure_id: str,
        arrival_id: str,
        outbound_date: str,        # "YYYY-MM-DD"
        return_date: str | None = None,  # set for round-trip
        timeout: int = 60,
    ) -> dict:
        """One live lookup. Returns the cheapest price plus Google's price-insights.

        For a round trip the first response already carries the total round-trip
        price, so a single call is enough for tracking (no departure_token needed).
        """
        params = {
            "engine": "google_flights",
            "departure_id": departure_id,
            "arrival_id": arrival_id,
            "outbound_date": outbound_date,
            "currency": self.currency,
            "hl": "en",
            "gl": "in",
            "api_key": self.api_key,
        }
        if return_date:
            params["type"] = 1            # round trip
            params["return_date"] = return_date
        else:
            params["type"] = 2            # one way

        resp = httpx.get(SERPAPI_URL, params=params, timeout=timeout, verify=CA_BUNDLE)
        resp.raise_for_status()
        data = resp.json()

        prices: list[float] = []
        for key in ("best_flights", "other_flights"):
            for flight in data.get(key, []) or []:
                if flight.get("price") is not None:
                    prices.append(float(flight["price"]))

        insights = data.get("price_insights") or {}
        return {
            "price": min(prices) if prices else None,
            "price_level": insights.get("price_level"),          # low / typical / high
            "typical_range": insights.get("typical_price_range"),  # [low, high]
        }
