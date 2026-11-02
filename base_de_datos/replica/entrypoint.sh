#!/bin/bash
# Entrypoint de la réplica: clona el primario con pg_basebackup la primera vez
# y arranca PostgreSQL en modo standby (streaming replication).
set -e
PGDATA="${PGDATA:-/var/lib/postgresql/data}"

if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo "[replica] Esperando al primario..."
  until pg_isready -h db-primary -p 5432 -U postgres >/dev/null 2>&1; do sleep 2; done
  echo "[replica] Clonando con pg_basebackup..."
  mkdir -p "$PGDATA"
  rm -rf "${PGDATA:?}"/* 2>/dev/null || true
  chown -R postgres:postgres "$PGDATA"
  chmod 700 "$PGDATA"
  gosu postgres pg_basebackup \
      -d "host=db-primary port=5432 user=replicator password=${REPL_PASSWORD}" \
      -D "$PGDATA" -R -X stream -S replica_slot -P
  echo "[replica] Clonado completo. Iniciando en modo standby."
fi

chown -R postgres:postgres "$PGDATA"
chmod 700 "$PGDATA"
exec gosu postgres postgres -c hot_standby=on -c wal_level=replica \
     -c max_wal_senders=10 -c max_replication_slots=10
