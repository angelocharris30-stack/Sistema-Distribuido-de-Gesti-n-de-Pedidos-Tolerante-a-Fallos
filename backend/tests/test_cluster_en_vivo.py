"""
Pruebas de integración contra el clúster REAL (docker compose up).
Se omiten salvo que se defina RUN_LIVE=1.

    RUN_LIVE=1 BASE_URL=http://localhost:8080 pytest tests/test_cluster_en_vivo.py -v
"""
import os
import uuid

import httpx
import pytest

BASE = os.getenv("BASE_URL", "http://localhost:8080")
pytestmark = pytest.mark.skipif(os.getenv("RUN_LIVE") != "1", reason="Defina RUN_LIVE=1 con el clúster levantado")

PEDIDO = {"cliente": "Prueba", "producto": "Item", "cantidad": 1, "precio_unitario": 10}


def test_balanceo_usa_ambos_nodos():
    nodos = {httpx.get(f"{BASE}/api/health").headers["x-node-id"] for _ in range(10)}
    assert nodos == {"api1", "api2"}


def test_escritura_y_lectura_consistente():
    r = httpx.post(f"{BASE}/api/pedidos", json=PEDIDO, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 201
    pid = r.json()["id"]
    leido = httpx.get(f"{BASE}/api/pedidos/{pid}", params={"consistent": "true"})
    assert leido.status_code == 200 and leido.json()["cliente"] == "Prueba"


def test_cluster_reporta_un_primario_y_una_replica():
    c = httpx.get(f"{BASE}/api/cluster").json()
    roles = sorted(d["role"] for d in c["db_nodes"] if d["up"])
    assert roles == ["primary", "replica"]


def test_renumeracion_sin_saltos_en_bd_real():
    a = httpx.post(f"{BASE}/api/pedidos", json=PEDIDO, headers={"Idempotency-Key": str(uuid.uuid4())}).json()
    b = httpx.post(f"{BASE}/api/pedidos", json=PEDIDO, headers={"Idempotency-Key": str(uuid.uuid4())}).json()
    assert httpx.delete(f"{BASE}/api/pedidos/{a['id']}").status_code == 204
    lista = httpx.get(f"{BASE}/api/pedidos", params={"consistent": "true"}).json()
    numeros = [p["numero"] for p in lista]
    assert numeros == list(range(1, len(lista) + 1))          # 1, 2, 3… sin saltos
    assert [p["id"] for p in lista] == sorted(p["id"] for p in lista)   # orden de llegada
    assert b["id"] in [p["id"] for p in lista]
