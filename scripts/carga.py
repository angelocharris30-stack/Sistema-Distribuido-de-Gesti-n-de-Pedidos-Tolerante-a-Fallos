#!/usr/bin/env python3
"""
Generador de carga para las pruebas de tolerancia a fallos (solo librería estándar).

Envía peticiones continuas al balanceador y muestra qué nodo respondió, el código
HTTP y la latencia. Mientras corre, apague/encienda contenedores en otra terminal.

    python scripts/carga.py --url http://localhost:8080 --duracion 60 --rps 4
"""
import argparse
import json
import time
import urllib.error
import urllib.request
import uuid
from collections import Counter


def llamar(url, metodo="GET", cuerpo=None, headers=None, timeout=6):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    h = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=datos, method=metodo, headers=h)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get("X-Node-Id", "?"), (time.perf_counter() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("X-Node-Id", "?"), (time.perf_counter() - t0) * 1000
    except Exception:
        return 0, "-", (time.perf_counter() - t0) * 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--duracion", type=int, default=60, help="segundos")
    ap.add_argument("--rps", type=float, default=4, help="ciclos por segundo")
    ap.add_argument("--reintentos", type=int, default=3, help="reintentos del cliente (como el frontend)")
    a = ap.parse_args()

    inicio = time.time()
    total = ok = 0
    por_nodo = Counter()
    por_codigo = Counter()
    fallos_seguidos = max_fallos_seguidos = 0
    lat = []
    n = 0

    print(f"{'t(s)':>6}  {'op':<5} {'HTTP':<5} {'nodo':<5} {'ms':>7}")
    while time.time() - inicio < a.duracion:
        n += 1
        if n % 2:
            op, metodo, ruta, cuerpo, hdr = "GET", "GET", "/api/pedidos", None, {}
        else:
            op, metodo, ruta = "POST", "POST", "/api/pedidos"
            cuerpo = {"cliente": "Carga", "producto": f"Item-{n}", "cantidad": 1, "precio_unitario": 10}
            hdr = {"Idempotency-Key": str(uuid.uuid4())}   # misma clave en los reintentos

        for intento in range(a.reintentos + 1):
            codigo, nodo, ms = llamar(a.url + ruta, metodo, cuerpo, hdr)
            if codigo in (200, 201, 204) or (400 <= codigo < 500):
                break
            time.sleep(0.4)

        total += 1
        por_codigo[codigo] += 1
        lat.append(ms)
        exito = codigo in (200, 201, 204)
        if exito:
            ok += 1
            por_nodo[nodo] += 1
            fallos_seguidos = 0
        else:
            fallos_seguidos += 1
            max_fallos_seguidos = max(max_fallos_seguidos, fallos_seguidos)
        marca = "" if exito else "  <-- ERROR"
        print(f"{time.time()-inicio:6.1f}  {op:<5} {codigo:<5} {nodo:<5} {ms:7.0f}{marca}")
        time.sleep(max(0, 1 / a.rps))

    lat.sort()
    print("\n=========== RESUMEN ===========")
    print(f"Peticiones lógicas : {total}")
    print(f"Exitosas           : {ok} ({100*ok/max(total,1):.1f}%)")
    print(f"Con error final    : {total-ok}")
    print(f"Racha máx. de fallos consecutivos: {max_fallos_seguidos}")
    print(f"Respuestas por nodo: {dict(por_nodo)}")
    print(f"Códigos HTTP       : {dict(por_codigo)}  (0 = sin respuesta)")
    if lat:
        print(f"Latencia ms        : mediana={lat[len(lat)//2]:.0f}  p95={lat[int(len(lat)*0.95)-1]:.0f}  máx={lat[-1]:.0f}")


if __name__ == "__main__":
    main()
