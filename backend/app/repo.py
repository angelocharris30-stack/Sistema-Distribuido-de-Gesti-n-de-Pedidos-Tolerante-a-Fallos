"""Operaciones sobre pedidos (SQL). Usa app.db para elegir el nodo adecuado."""
from . import db
from .estados import transicion_valida


class NoEncontrado(Exception):
    pass


class Conflicto(Exception):
    pass


COLS = ("id, cliente, producto, cantidad, precio_unitario, estado, version, "
        "created_at, updated_at")

# Número de pedido que ve el usuario: posición (por orden de llegada) entre los
# pedidos NO eliminados. Se recalcula en cada consulta, así que al borrar pedidos
# los siguientes "bajan" y nunca quedan saltos: 1, 2, 3…
NUM = ("(SELECT count(*) FROM pedidos q "
       "WHERE q.deleted_at IS NULL AND q.id <= pedidos.id)::int AS numero")
COLS_N = f"{COLS}, {NUM}"


def _fix(row):
    if row is None:
        return None
    row = dict(row)
    row["precio_unitario"] = float(row["precio_unitario"])
    row["total"] = round(row["cantidad"] * row["precio_unitario"], 2)
    return row


def _get(cur, pedido_id):
    cur.execute(f"SELECT {COLS_N} FROM pedidos WHERE id=%s", (pedido_id,))
    return _fix(cur.fetchone())


def crear(data, idempotency_key=None):
    """Devuelve (pedido, creado). Con la misma Idempotency-Key no duplica."""
    def op(cur):
        cur.execute(
            "INSERT INTO pedidos (cliente, producto, cantidad, precio_unitario, idempotency_key) "
            "VALUES (%s,%s,%s,%s,%s) ON CONFLICT (idempotency_key) DO NOTHING RETURNING id",
            (data.cliente, data.producto, data.cantidad, data.precio_unitario, idempotency_key),
        )
        row = cur.fetchone()
        if row:
            return _get(cur, row["id"]), True
        cur.execute("SELECT id FROM pedidos WHERE idempotency_key=%s", (idempotency_key,))
        return _get(cur, cur.fetchone()["id"]), False
    return db.run_write(op)


def listar(estado=None, consistent=False):
    def op(cur):
        sql = f"SELECT {COLS_N} FROM pedidos WHERE deleted_at IS NULL"
        params = []
        if estado:
            sql += " AND estado=%s"
            params.append(estado)
        cur.execute(sql + " ORDER BY id ASC", params)  # orden de llegada: el primero que entra, primero
        return [_fix(r) for r in cur.fetchall()]
    return db.run_read(op, consistent)


def obtener(pedido_id, consistent=False):
    def op(cur):
        cur.execute(f"SELECT {COLS_N} FROM pedidos WHERE id=%s AND deleted_at IS NULL", (pedido_id,))
        row = cur.fetchone()
        if not row:
            raise NoEncontrado(f"Pedido {pedido_id} no existe")
        return _fix(row)
    return db.run_read(op, consistent)


def actualizar(pedido_id, data):
    def op(cur):
        cur.execute(
            "UPDATE pedidos SET cliente=%s, producto=%s, cantidad=%s, precio_unitario=%s, "
            "version=version+1, updated_at=now() "
            "WHERE id=%s AND deleted_at IS NULL AND version=%s RETURNING id",
            (data.cliente, data.producto, data.cantidad, data.precio_unitario,
             pedido_id, data.version),
        )
        row = cur.fetchone()
        if row:
            return _get(cur, row["id"])
        cur.execute("SELECT version FROM pedidos WHERE id=%s AND deleted_at IS NULL", (pedido_id,))
        actual = cur.fetchone()
        if not actual:
            raise NoEncontrado(f"Pedido {pedido_id} no existe")
        raise Conflicto(f"Versión desactualizada: enviaste {data.version}, la actual es {actual['version']}")
    return db.run_write(op)


def cambiar_estado(pedido_id, nuevo, version):
    def op(cur):
        cur.execute(
            f"SELECT {COLS} FROM pedidos WHERE id=%s AND deleted_at IS NULL FOR UPDATE", (pedido_id,)
        )
        row = cur.fetchone()
        if not row:
            raise NoEncontrado(f"Pedido {pedido_id} no existe")
        if row["version"] != version:
            raise Conflicto(f"Versión desactualizada: enviaste {version}, la actual es {row['version']}")
        if not transicion_valida(row["estado"], nuevo):
            raise Conflicto(f"Transición inválida: {row['estado']} -> {nuevo}")
        cur.execute(
            "UPDATE pedidos SET estado=%s, version=version+1, updated_at=now() "
            "WHERE id=%s", (nuevo, pedido_id),
        )
        return _get(cur, pedido_id)
    return db.run_write(op)


def eliminar(pedido_id):
    """Borrado lógico."""
    def op(cur):
        cur.execute(
            "UPDATE pedidos SET deleted_at=now(), version=version+1, updated_at=now() "
            "WHERE id=%s AND deleted_at IS NULL RETURNING id", (pedido_id,),
        )
        if not cur.fetchone():
            raise NoEncontrado(f"Pedido {pedido_id} no existe")
    return db.run_write(op)
