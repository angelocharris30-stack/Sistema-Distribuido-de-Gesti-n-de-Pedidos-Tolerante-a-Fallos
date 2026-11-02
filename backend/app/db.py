"""
Acceso a la base de datos con detección automática de roles.

- Escrituras  -> siempre al nodo que NO está en recuperación (el primario;
                 tras una promoción, la antigua réplica).
- Lecturas    -> se intenta primero la réplica; si cae, se usa el primario.
- Si una conexión falla a mitad de operación se reintenta una vez.
"""
import os
import time

import psycopg2
from psycopg2.extras import RealDictCursor

HOSTS = [h.strip() for h in os.getenv("DB_HOSTS", "db-primary,db-replica").split(",") if h.strip()]
PORT = int(os.getenv("DB_PORT", "5432"))
NAME = os.getenv("DB_NAME", "pedidos")
USER = os.getenv("DB_USER", "postgres")
PASSWORD = os.getenv("DB_PASSWORD", "pedidos_pw")
CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "2"))

_writer_cache = None


class DatabaseUnavailable(Exception):
    """Ningún nodo de base de datos puede atender la operación."""


def _connect(host):
    return psycopg2.connect(
        host=host, port=PORT, dbname=NAME, user=USER, password=PASSWORD,
        connect_timeout=CONNECT_TIMEOUT, cursor_factory=RealDictCursor,
    )


def _en_recuperacion(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT pg_is_in_recovery() AS r")
        r = cur.fetchone()["r"]
    conn.rollback()
    return bool(r)


def _reset_cache():
    global _writer_cache
    _writer_cache = None


def connect_writer():
    """Conexión al nodo escritor (el que no está en modo réplica)."""
    global _writer_cache
    orden = ([_writer_cache] if _writer_cache else []) + [h for h in HOSTS if h != _writer_cache]
    for host in orden:
        try:
            conn = _connect(host)
        except psycopg2.OperationalError:
            continue
        try:
            if not _en_recuperacion(conn):
                _writer_cache = host
                return conn
        except Exception:
            pass
        conn.close()
    _reset_cache()
    raise DatabaseUnavailable("No hay ningún nodo de base de datos con permiso de escritura")


def connect_reader():
    """Conexión de lectura: réplica primero (orden inverso), primario como respaldo."""
    for host in reversed(HOSTS):
        try:
            return _connect(host)
        except psycopg2.OperationalError:
            continue
    raise DatabaseUnavailable("No hay ningún nodo de base de datos disponible para lectura")


def run_write(fn):
    """Ejecuta fn(cursor) en una transacción sobre el escritor, con 1 reintento."""
    ultimo = None
    for _ in range(2):
        try:
            conn = connect_writer()
        except DatabaseUnavailable as e:
            ultimo = e
            time.sleep(0.3)
            continue
        try:
            with conn.cursor() as cur:
                resultado = fn(cur)
            conn.commit()
            return resultado
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            ultimo = e
            _reset_cache()
        except Exception:
            conn.rollback()
            raise
        finally:
            try:
                conn.close()
            except Exception:
                pass
    raise DatabaseUnavailable(str(ultimo))


def run_read(fn, consistent=False):
    """Ejecuta fn(cursor) de solo lectura. consistent=True fuerza leer del escritor."""
    ultimo = None
    for _ in range(2):
        try:
            conn = connect_writer() if consistent else connect_reader()
        except DatabaseUnavailable as e:
            ultimo = e
            time.sleep(0.3)
            continue
        try:
            with conn.cursor() as cur:
                resultado = fn(cur)
            conn.rollback()
            return resultado
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            ultimo = e
            _reset_cache()
        finally:
            try:
                conn.close()
            except Exception:
                pass
    raise DatabaseUnavailable(str(ultimo))


def inspeccionar(host) -> dict:
    """Estado de un nodo de BD para el panel de monitoreo."""
    info = {"host": host, "up": False, "role": None, "detail": None}
    try:
        conn = _connect(host)
    except psycopg2.OperationalError as e:
        info["detail"] = str(e).strip().splitlines()[0][:120]
        return info
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_is_in_recovery() AS r")
            replica = cur.fetchone()["r"]
            info["up"] = True
            info["role"] = "replica" if replica else "primary"
            if replica:
                cur.execute(
                    "SELECT COALESCE(pg_wal_lsn_diff(pg_last_wal_receive_lsn(), "
                    "pg_last_wal_replay_lsn()),0)::bigint AS lag"
                )
                info["detail"] = f"retraso de replay: {cur.fetchone()['lag']} bytes"
            else:
                cur.execute("SELECT count(*) AS n FROM pg_stat_replication")
                info["detail"] = f"réplicas conectadas: {cur.fetchone()['n']}"
    except Exception as e:
        info["detail"] = str(e).strip().splitlines()[0][:120]
    finally:
        conn.close()
    return info
