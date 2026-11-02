#!/bin/bash
# Promueve la réplica a primario (failover manual de base de datos).
# Úsese después de `docker stop db-primary`.
set -e
docker compose exec -T db-replica psql -U postgres -d pedidos -c "SELECT pg_promote(wait := true);"
echo "Réplica promovida. La API detecta el nuevo escritor automáticamente."
