"""Gemensamma kostnadsregler för FlipFynd.

Håller filtrering och analys synkroniserade så samma annons aldrig bedöms med
olika inköpskostnad i olika delar av appen.
"""

DEFAULT_UNKNOWN_SHIPPING = 29


def normalize_shipping(value, default=DEFAULT_UNKNOWN_SHIPPING):
    """Returnera användbar fraktkostnad; okänd frakt får ett försiktigt antagande."""
    if value is None:
        return float(default)
    if isinstance(value, (int, float)) and value >= 0:
        return float(value)
    return float(default)


def total_acquisition_cost(price, shipping=None):
    """Pris + normaliserad frakt, eller None om priset är ogiltigt."""
    if not isinstance(price, (int, float)) or price <= 0:
        return None
    return float(price) + normalize_shipping(shipping)
