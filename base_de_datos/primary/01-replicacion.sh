#!/bin/bash
# Se ejecuta UNA vez al inicializar el primario (docker-entrypoint-initdb.d).
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD '${REPL_PASSWORD}';
SELECT pg_create_physical_replication_slot('replica_slot');
EOSQL
# Permitir conexiones de replicación desde la red de Docker
echo "host replication replicator all scram-sha-256" >> "$PGDATA/pg_hba.conf"
