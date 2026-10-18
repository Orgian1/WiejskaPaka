"""Jawny kontrakt skali pilotażu PL; nie stanowi gwarancji wydajności.

Liczba klientów to dzienni użytkownicy, nie jednoczesne połączenia.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class CapacityTarget:
    market: str = "PL"
    currency: str = "PLN"
    sellers: int = 50
    buyers_per_day: int = 5000
    buyers_peak_hour_fraction_percent: int = 20
    page_requests_per_buyer: int = 20

    def __post_init__(self):
        if self.market != "PL" or self.currency != "PLN":
            raise ValueError("Ten projekt obsługuje wyłącznie polski rynek i PLN")
        for field in ("sellers", "buyers_per_day", "page_requests_per_buyer"):
            value = getattr(self, field)
            if type(value) is not int or value <= 0:
                raise ValueError("Wielkości obciążenia muszą być dodatnimi liczbami całkowitymi")
        pct = self.buyers_peak_hour_fraction_percent
        if type(pct) is not int or not 1 <= pct <= 100:
            raise ValueError("Udział godziny szczytu musi wynosić 1–100 procent")

    @property
    def requests_per_day(self):
        return self.buyers_per_day * self.page_requests_per_buyer

    @property
    def peak_hour_requests(self):
        return (self.requests_per_day * self.buyers_peak_hour_fraction_percent + 99) // 100

    @property
    def peak_requests_per_second(self):
        return (self.peak_hour_requests + 3599) // 3600


PILOT = CapacityTarget(sellers=20, buyers_per_day=1000)
FIRST_TARGET = CapacityTarget()


def planning_report(target=FIRST_TARGET):
    return {
        "market": target.market,
        "currency": target.currency,
        "sellers": target.sellers,
        "buyers_per_day": target.buyers_per_day,
        "assumed_page_requests_per_buyer": target.page_requests_per_buyer,
        "assumed_peak_hour_share_percent": target.buyers_peak_hour_fraction_percent,
        "estimated_requests_per_day": target.requests_per_day,
        "estimated_peak_requests_per_second": target.peak_requests_per_second,
        "capacity_verified": False,
        "note": "Założenia planistyczne, nie wynik testu HTTP/PostgreSQL; przed wdrożeniem wykonaj pomiar.",
    }
