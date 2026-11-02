"""Máquina de estados de un pedido (lógica pura, sin dependencias)."""

ORDEN = ["pendiente", "en_proceso", "enviado", "entregado"]


def siguiente(actual: str):
    """Devuelve el estado siguiente o None si ya es el último."""
    i = ORDEN.index(actual)
    return ORDEN[i + 1] if i + 1 < len(ORDEN) else None


def anterior(actual: str):
    """Devuelve el estado anterior o None si ya es el primero."""
    i = ORDEN.index(actual)
    return ORDEN[i - 1] if i > 0 else None


def transicion_valida(actual: str, nuevo: str) -> bool:
    """
    Se permite avanzar un paso o RETROCEDER un paso (para corregir un error
    humano). Los saltos de más de un paso y quedarse igual se rechazan.
    """
    if actual not in ORDEN or nuevo not in ORDEN:
        return False
    return abs(ORDEN.index(nuevo) - ORDEN.index(actual)) == 1
