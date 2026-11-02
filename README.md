# Sistema Distribuido de Gestión de Pedidos Tolerante a Fallos

de un nodo de aplicación o de la base de datos.

```
Navegador ──► NGINX (balanceador + frontend) ──► api1 ─┐
                                              └─► api2 ─┼─► PostgreSQL primario ══replicación══► PostgreSQL réplica
```

| Capa | Tecnología | Tolerancia a fallos |
|---|---|---|
| Frontend | React + Vite | Reintentos automáticos, idempotencia, panel de monitoreo |
| Balanceo | NGINX | Round-robin, `max_fails`, `proxy_next_upstream` |
| Aplicación | FastAPI (2 nodos sin estado) | Cualquier nodo atiende cualquier petición |
| Datos | PostgreSQL 16 | Replicación en streaming + promoción de la réplica |

## Requisitos
- Docker Desktop (o Docker Engine) con **Docker Compose v2**
- Python 3.10+ (solo para pruebas y script de carga)
- Puertos libres: `8080`, `5432`, `5433`

## Despliegue (un solo comando)
```bash
docker compose up --build -d
docker compose ps          # esperar a que todos estén "healthy" (≈ 1 min la primera vez)
```
- Aplicación: http://localhost:8080
- Documentación Swagger de la API: http://localhost:8080/api/docs
- Monitoreo: pestaña **Monitoreo del clúster** en la aplicación

Verificar la replicación:
```bash
docker compose exec db-replica psql -U postgres -d pedidos -c "SELECT pg_is_in_recovery();"   # → t
docker compose exec db-primary psql -U postgres -d pedidos -c "SELECT client_addr,state FROM pg_stat_replication;"
```
## Pruebas
```bash
cd backend
pip install -r requirements-dev.txt
pytest -v                                            # unitarias + API (sin base de datos)
RUN_LIVE=1 BASE_URL=http://localhost:8080 pytest tests/test_cluster_en_vivo.py -v   # contra el clúster real
```
(En Windows PowerShell: `$env:RUN_LIVE=1; pytest tests/test_cluster_en_vivo.py -v`)

## Simulación de fallos
Terminal A — carga continua:
```bash
python scripts/carga.py --url http://localhost:8080 --duracion 60 --rps 4
```
Terminal B — provocar fallos mientras corre la carga:
```bash
docker stop api1                 # cae un nodo de aplicación  → 0 errores, atiende api2
docker start api1                # se reincorpora solo
docker stop db-replica           # lecturas pasan al primario
docker start db-replica
docker stop db-primary           # escrituras → 503 temporal; lecturas siguen
bash scripts/promote.sh          # promueve la réplica → escrituras restablecidas
```
Windows sin bash: `docker compose exec -T db-replica psql -U postgres -d pedidos -c "SELECT pg_promote(wait := true);"`

## Estructura
```
frontend/   React + Vite (UI de pedidos y panel de monitoreo)
backend/    FastAPI (app/), pruebas (tests/), Dockerfile
base_de_datos/   primary/ (rol de replicación + esquema), replica/ (clonado y standby)
nginx/      nginx.conf + Dockerfile (compila el frontend y lo sirve)
scripts/    carga.py (generador de carga), promote.sh (failover de BD)
docs/       1_Manual_Tecnico, 2_Manual_de_Usuario, 3_Informe_de_Pruebas (Word) + diagramas
docker-compose.yml
```

## Decisiones de diseño relevantes
- **Idempotencia**: `POST /api/pedidos` acepta `Idempotency-Key`; un reintento nunca duplica.
- **Control optimista**: columna `version`; una edición con versión vieja devuelve `409`.
- **Máquina de estados**: pendiente → en_proceso → enviado → entregado. Se puede avanzar o **retroceder un paso** para corregir errores; los saltos de varios pasos se rechazan (409). En la interfaz, el cambio de estado está dentro de **Editar** (bloque «Flujo del pedido»).
- **Numeración consecutiva**: el número que se ve (#1, #2, #3…) es la posición por orden de llegada y se calcula en cada consulta; al eliminar pedidos los demás se renumeran y no quedan saltos. El `id` interno solo se usa en las rutas de la API.
- **Borrado lógico** (`deleted_at`) para mantener consistente la réplica.
- **Detección automática del escritor**: la API consulta `pg_is_in_recovery()`; tras `promote.sh`
  usa la antigua réplica sin reiniciar nada.
- Cada respuesta incluye `X-Node-Id` para ver qué nodo atendió.

## Limitaciones conocidas
- NGINX es un punto único de fallo (solución: 2 instancias + keepalived/VIP).
- Replicación **asíncrona**: una lectura en la réplica puede ir unos ms atrasada. Tras escribir,
  el frontend lee del primario (`?consistent=true`).
- La promoción de la réplica es **manual** (`promote.sh`); automatizarla requiere Patroni o similar.
- Tras una promoción, el antiguo primario no se reincorpora automáticamente como réplica.
