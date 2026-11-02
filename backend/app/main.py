import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from fastapi import FastAPI, Header, Query, Request, Response
from fastapi.responses import JSONResponse

from . import db, repo
from .schemas import Estado, EstadoUpdate, PedidoIn, PedidoOut, PedidoUpdate

NODE_ID = os.getenv("NODE_ID", "api-local")
PEERS = [p.strip() for p in os.getenv("PEERS", "").split(",") if p.strip()]

app = FastAPI(
    title="Sistema Distribuido de Gestión de Pedidos",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


@app.middleware("http")
async def cabecera_nodo(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Node-Id"] = NODE_ID
    return response


@app.exception_handler(repo.NoEncontrado)
async def _no_encontrado(_: Request, exc: repo.NoEncontrado):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(repo.Conflicto)
async def _conflicto(_: Request, exc: repo.Conflicto):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(db.DatabaseUnavailable)
async def _bd_no_disponible(_: Request, exc: db.DatabaseUnavailable):
    return JSONResponse(
        status_code=503,
        content={"detail": "Base de datos no disponible temporalmente. Reintente."},
        headers={"Retry-After": "2"},
    )


# ---------------------------------------------------------------- salud
@app.get("/api/health")
def health():
    """Liveness del nodo (no consulta la BD para ser rápido y fiable)."""
    return {"status": "ok", "node": NODE_ID}


def _consultar_peer(url: str) -> dict:
    nombre = url.split("//")[-1].split(":")[0]
    try:
        with urllib.request.urlopen(f"{url}/api/health", timeout=1.5) as r:
            data = json.loads(r.read())
            return {"node": data.get("node", nombre), "url": url, "up": True}
    except Exception:
        return {"node": nombre, "url": url, "up": False}


@app.get("/api/cluster")
def cluster():
    """Estado de todo el clúster (nodos de aplicación y de base de datos)."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        f_nodes = [pool.submit(_consultar_peer, p) for p in PEERS]
        f_dbs = [pool.submit(db.inspeccionar, h) for h in db.HOSTS]
        nodes = [f.result() for f in f_nodes]
        dbs = [f.result() for f in f_dbs]
    return {"answered_by": NODE_ID, "api_nodes": nodes, "db_nodes": dbs}


# -------------------------------------------------------------- pedidos
@app.post("/api/pedidos", response_model=PedidoOut, status_code=201)
def crear_pedido(
    data: PedidoIn,
    response: Response,
    idempotency_key: Optional[str] = Header(default=None, max_length=100),
):
    pedido, creado = repo.crear(data, idempotency_key)
    if not creado:
        response.status_code = 200
        response.headers["Idempotent-Replay"] = "true"
    return pedido


@app.get("/api/pedidos", response_model=List[PedidoOut])
def listar_pedidos(
    estado: Optional[Estado] = Query(default=None),
    consistent: bool = Query(default=False, description="Leer del primario (sin retraso de réplica)"),
):
    return repo.listar(estado, consistent)


@app.get("/api/pedidos/{pedido_id}", response_model=PedidoOut)
def obtener_pedido(pedido_id: int, consistent: bool = False):
    return repo.obtener(pedido_id, consistent)


@app.put("/api/pedidos/{pedido_id}", response_model=PedidoOut)
def actualizar_pedido(pedido_id: int, data: PedidoUpdate):
    return repo.actualizar(pedido_id, data)


@app.patch("/api/pedidos/{pedido_id}/estado", response_model=PedidoOut)
def cambiar_estado(pedido_id: int, data: EstadoUpdate):
    return repo.cambiar_estado(pedido_id, data.estado, data.version)


@app.delete("/api/pedidos/{pedido_id}", status_code=204)
def eliminar_pedido(pedido_id: int):
    repo.eliminar(pedido_id)
    return Response(status_code=204)
