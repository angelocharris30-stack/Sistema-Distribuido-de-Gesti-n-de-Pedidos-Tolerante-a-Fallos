"""Pruebas unitarias de validación de datos (Pydantic)."""
import pytest
from pydantic import ValidationError

from app.schemas import EstadoUpdate, PedidoIn


def test_pedido_valido():
    p = PedidoIn(cliente="Ana", producto="Teclado", cantidad=2, precio_unitario="49.90")
    assert p.cantidad == 2


@pytest.mark.parametrize("campo,valor", [
    ("cantidad", 0), ("cantidad", -3),
    ("precio_unitario", 0), ("precio_unitario", -1),
    ("cliente", ""), ("producto", ""),
])
def test_pedido_invalido(campo, valor):
    datos = dict(cliente="Ana", producto="Teclado", cantidad=1, precio_unitario=10)
    datos[campo] = valor
    with pytest.raises(ValidationError):
        PedidoIn(**datos)


def test_estado_inexistente_rechazado():
    with pytest.raises(ValidationError):
        EstadoUpdate(estado="cancelado", version=1)
