"""Pruebas de integración de la API HTTP (capa de datos en memoria)."""
PEDIDO = {"cliente": "Ana", "producto": "Teclado", "cantidad": 2, "precio_unitario": 49.9}


def test_health_incluye_nodo(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert "x-node-id" in r.headers


def test_crear_y_listar(client):
    r = client.post("/api/pedidos", json=PEDIDO)
    assert r.status_code == 201
    creado = r.json()
    assert creado["estado"] == "pendiente" and creado["version"] == 1
    assert creado["total"] == 99.8
    lista = client.get("/api/pedidos").json()
    assert [p["id"] for p in lista] == [creado["id"]]


def test_idempotencia_no_duplica(client):
    h = {"Idempotency-Key": "abc-123"}
    r1 = client.post("/api/pedidos", json=PEDIDO, headers=h)
    r2 = client.post("/api/pedidos", json=PEDIDO, headers=h)
    assert r1.status_code == 201
    assert r2.status_code == 200
    assert r2.headers["idempotent-replay"] == "true"
    assert r1.json()["id"] == r2.json()["id"]
    assert len(client.get("/api/pedidos").json()) == 1


def test_validacion_devuelve_422(client):
    r = client.post("/api/pedidos", json={**PEDIDO, "cantidad": 0})
    assert r.status_code == 422


def test_actualizar_con_version_obsoleta_da_409(client):
    p = client.post("/api/pedidos", json=PEDIDO).json()
    ok = client.put(f"/api/pedidos/{p['id']}", json={**PEDIDO, "cantidad": 5, "version": 1})
    assert ok.status_code == 200 and ok.json()["version"] == 2
    viejo = client.put(f"/api/pedidos/{p['id']}", json={**PEDIDO, "cantidad": 9, "version": 1})
    assert viejo.status_code == 409


def test_retroceso_de_estado_para_corregir_errores(client):
    pid = client.post("/api/pedidos", json=PEDIDO).json()["id"]
    url = f"/api/pedidos/{pid}/estado"

    def cambiar(estado, version):
        return client.patch(url, json={"estado": estado, "version": version})

    a = cambiar("en_proceso", 1).json()
    b = cambiar("enviado", a["version"]).json()
    # el usuario se equivocó: vuelve de "enviado" a "en_proceso" (un paso atrás)
    atras = cambiar("en_proceso", b["version"])
    assert atras.status_code == 200 and atras.json()["estado"] == "en_proceso"
    # y otro paso atrás, hasta "pendiente"
    inicio = cambiar("pendiente", atras.json()["version"])
    assert inicio.status_code == 200 and inicio.json()["estado"] == "pendiente"
    # desde "pendiente" no se puede saltar a "enviado"
    assert cambiar("enviado", inicio.json()["version"]).status_code == 409


def test_flujo_de_estados_y_salto_invalido(client):
    p = client.post("/api/pedidos", json=PEDIDO).json()
    salto = client.patch(f"/api/pedidos/{p['id']}/estado", json={"estado": "enviado", "version": 1})
    assert salto.status_code == 409
    paso = client.patch(f"/api/pedidos/{p['id']}/estado", json={"estado": "en_proceso", "version": 1})
    assert paso.status_code == 200 and paso.json()["estado"] == "en_proceso"


def test_filtrar_por_estado(client):
    a = client.post("/api/pedidos", json=PEDIDO).json()
    client.post("/api/pedidos", json=PEDIDO)
    client.patch(f"/api/pedidos/{a['id']}/estado", json={"estado": "en_proceso", "version": 1})
    assert len(client.get("/api/pedidos?estado=en_proceso").json()) == 1
    assert len(client.get("/api/pedidos?estado=pendiente").json()) == 1


def test_numeracion_consecutiva_y_orden_de_llegada(client):
    a = client.post("/api/pedidos", json=PEDIDO, headers={"Idempotency-Key": "k1"}).json()
    client.post("/api/pedidos", json=PEDIDO, headers={"Idempotency-Key": "k1"})  # reintento: no duplica
    b = client.post("/api/pedidos", json=PEDIDO).json()
    c = client.post("/api/pedidos", json=PEDIDO).json()
    assert [a["numero"], b["numero"], c["numero"]] == [1, 2, 3]
    # el primero que entra aparece primero
    assert [p["numero"] for p in client.get("/api/pedidos").json()] == [1, 2, 3]


def test_renumeracion_al_eliminar_sin_saltos(client):
    ids = [client.post("/api/pedidos", json=PEDIDO).json()["id"] for _ in range(3)]
    # se elimina el del medio: los que quedan siguen siendo 1, 2 (sin salto)
    assert client.delete(f"/api/pedidos/{ids[1]}").status_code == 204
    lista = client.get("/api/pedidos").json()
    assert [p["numero"] for p in lista] == [1, 2]
    assert [p["id"] for p in lista] == [ids[0], ids[2]]
    # se eliminan todos y el siguiente pedido vuelve a ser el #1
    for i in (ids[0], ids[2]):
        client.delete(f"/api/pedidos/{i}")
    nuevo = client.post("/api/pedidos", json=PEDIDO).json()
    assert nuevo["numero"] == 1


def test_borrado_logico_y_404(client):
    p = client.post("/api/pedidos", json=PEDIDO).json()
    assert client.delete(f"/api/pedidos/{p['id']}").status_code == 204
    assert client.get(f"/api/pedidos/{p['id']}").status_code == 404
    assert client.delete(f"/api/pedidos/{p['id']}").status_code == 404
    assert client.get("/api/pedidos").json() == []
