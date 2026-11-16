"""Pure PayU top-up request validation; does not initiate payments."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TopupIntent:
    operation_id: str
    user_id: int
    amount_grosze: int
    currency: str = "PLN"

    def __post_init__(self):
        if not isinstance(self.operation_id, str) or not 1 <= len(self.operation_id) <= 120:
            raise ValueError("Invalid top-up operation identifier")
        if type(self.user_id) is not int or self.user_id <= 0:
            raise ValueError("Invalid top-up user")
        if type(self.amount_grosze) is not int or self.amount_grosze <= 0:
            raise ValueError("Top-up amount must be positive integer grosze")
        if self.currency != "PLN":
            raise ValueError("Only PLN top-ups are supported")
