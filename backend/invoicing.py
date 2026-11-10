"""Non-fiscal commission preview. Amounts in integer grosze only."""

def calculate_commission_grosze(basis_grosze: int, rate_basis_points: int) -> int:
    """Round half-up to grosz; 10000 basis points = 100%."""
    if type(basis_grosze) is not int or not (0 <= basis_grosze <= 9_000_000_000_000):
        raise ValueError('Nieprawidłowa podstawa w groszach')
    if type(rate_basis_points) is not int or not (0 <= rate_basis_points <= 10000):
        raise ValueError('Nieprawidłowa stawka w punktach bazowych')
    return (basis_grosze * rate_basis_points + 5000) // 10000
