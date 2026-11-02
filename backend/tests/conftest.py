"""
Fixture que reemplaza la capa de datos por una implementación en memoria,
de modo que las pruebas de la API HTTP no necesitan PostgreSQL.
"""
import itertools
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app import repo as repo_real
from app.estados import transicion_valida


class RepoEnMemoria:
    NoEncontrado = repo_real.NoEncontrado
    Conflicto = repo_real.Conflicto

    def __init__(self):
        self.filas = {}
        self.claves = {}
        self.ids = itertools.count(1)

    def _numero(self, i):
        """Posición por orden de llegada entre los pedidos no eliminados (igual que el SQL real)."""
        return sum(1 for f in self.filas.values() if not f["deleted"] and f["id"] <= i)

    def _out(self, f):
        d = dict(f)
        d["numero"] = self._numero(f["id"])
        d["precio_unitario"] = float(d["precio_unitario"])
        d["total"] = round(d["cantidad"] * d["precio_unitario"], 2)
        return d

    def crear(self, data, key=None):
        if key and key in self.claves:
            return self._out(self.filas[self.claves[key]]), False
        i = next(self.ids)
        ahora = datetime.now(timezone.utc)
        self.filas[i] = dict(id=i, cliente=data.cliente, producto=data.producto,
                             cantidad=data.cantidad, precio_unitario=data.precio_unitario,
                             estado="pendiente", version=1, created_at=ahora,
                             updated_at=ahora, deleted=False)
        if key:
            self.claves[key] = i
        return self._out(self.filas[i]), True

    def listar(self, estado=None, consistent=False):
        return [self._out(f) for f in sorted(self.filas.values(), key=lambda x: x["id"])
                if not f["deleted"] and (not estado or f["estado"] == estado)]

    def _get(self, i):
        f = self.filas.get(i)
        if not f or f["deleted"]:
            raise repo_real.NoEncontrado(f"Pedido {i} no existe")
        return f

    def obtener(self, i, consistent=False):
        return self._out(self._get(i))

    def actualizar(self, i, data):
        f = self._get(i)
        if f["version"] != data.version:
            raise repo_real.Conflicto("Versión desactualizada")
        f.update(cliente=data.cliente, producto=data.producto, cantidad=data.cantidad,
                 precio_unitario=data.precio_unitario, version=f["version"] + 1)
        return self._out(f)

    def cambiar_estado(self, i, nuevo, version):
        f = self._get(i)
        if f["version"] != version:
            raise repo_real.Conflicto("Versión desactualizada")
        if not transicion_valida(f["estado"], nuevo):
            raise repo_real.Conflicto("Transición inválida")
        f.update(estado=nuevo, version=f["version"] + 1)
        return self._out(f)

    def eliminar(self, i):
        self._get(i)["deleted"] = True


@pytest.fixture
def client(monkeypatch):
    from app import main
    monkeypatch.setattr(main, "repo", RepoEnMemoria())
    return TestClient(main.app)
