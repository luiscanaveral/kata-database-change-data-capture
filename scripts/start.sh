#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "  CDC PoC — Ticket Platform"
echo "============================================"
echo ""

cd "$PROJECT_DIR"

echo "[1/4] Building images and starting services..."
docker compose up -d --build
echo ""

echo "[2/4] Waiting for Kafka Connect to be healthy..."
until curl -s -o /dev/null -w "%{http_code}" http://localhost:8083/connectors | grep -q "200"; do
  printf '.'
  sleep 2
done
echo " OK"
echo ""

echo "[3/4] Registering Debezium PostgreSQL connector..."
bash "$SCRIPT_DIR/register-postgres-connector.sh"
echo ""

echo "[4/4] Setup complete!"
echo ""
echo "Services:"
echo "  PostgreSQL  : postgres:5432 (localhost:5432)"
echo "  Kafka       : kafka:9092 (localhost:29092)"
echo "  Debezium    : localhost:8083"
echo "  Kafka UI    : http://localhost:8080"
echo "  Azurite     : http://localhost:10000"
echo "  Sink        : consuming ticketdb.public.* -> cdc-events container"
echo "  Simulator   : generating data every 15s"
echo ""
echo "CDC events are being stored in Azurite blob container 'cdc-events'"
echo "Browse them at: http://localhost:10000/devstoreaccount1/cdc-events"
echo ""
echo "To stop:  docker compose down"
echo "To reset: docker compose down -v"
