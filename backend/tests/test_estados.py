"""Pruebas unitarias de la máquina de estados."""
import pytest

from app.estados import ORDEN, anterior, siguiente, transicion_valida


def test_avance_de_un_paso_valido():
    for a, b in zip(ORDEN, ORDEN[1:]):
        assert transicion_valida(a, b)


def test_retroceso_de_un_paso_valido():
    """Corregir un error: se puede volver un paso atrás."""
    for a, b in zip(ORDEN[1:], ORDEN):
        assert transicion_valida(a, b)


@pytest.mark.parametrize("a,b", [
    ("pendiente", "enviado"),       # salto adelante
    ("pendiente", "entregado"),     # salto adelante
    ("entregado", "pendiente"),     # salto atrás de 3 pasos
    ("enviado", "pendiente"),       # salto atrás de 2 pasos
    ("pendiente", "pendiente"),     # mismo estado
    ("pendiente", "cancelado"),     # estado inexistente
])
def test_transiciones_invalidas(a, b):
    assert not transicion_valida(a, b)


def test_siguiente():
    assert siguiente("pendiente") == "en_proceso"
    assert siguiente("entregado") is None


def test_anterior():
    assert anterior("entregado") == "enviado"
    assert anterior("pendiente") is None
