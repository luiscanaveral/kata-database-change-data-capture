#!/bin/bash
set -e

echo "Waiting for Kafka Connect at localhost:8083 ..."
until curl -s -o /dev/null -w "%{http_code}" http://localhost:8083/connectors | grep -q "200"; do
  printf '.'
  sleep 2
done
echo ""
echo "Kafka Connect is ready."

CONNECTOR_CONFIG='{
  "name": "ticketdb-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "postgres",
    "database.dbname": "ticketdb",
    "database.server.name": "ticketdb",
    "table.include.list": "public.venues,public.artists,public.events,public.event_artists,public.sections,public.customers,public.orders,public.order_items",
    "plugin.name": "pgoutput",
    "publication.autocreate.mode": "all_tables",
    "slot.name": "dbz_ticket_slot",
    "publication.name": "dbz_ticket_pub",
    "tombstones.on.delete": "false"
  }
}'

echo "Registering Debezium PostgreSQL connector..."
HTTP_CODE=$(curl -s -o /tmp/connector_response.txt -w "%{http_code}" \
  -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d "$CONNECTOR_CONFIG")

if [ "$HTTP_CODE" = "201" ]; then
  echo "Connector registered successfully!"
elif [ "$HTTP_CODE" = "409" ]; then
  echo "Connector already exists — updating config instead..."
  curl -s -X PUT http://localhost:8083/connectors/ticketdb-connector/config \
    -H "Content-Type: application/json" \
    -d "$(echo "$CONNECTOR_CONFIG" | jq -r '.config')"
else
  echo "Unexpected HTTP $HTTP_CODE:"
  cat /tmp/connector_response.txt
  exit 1
fi

echo ""
echo "Connector status:"
curl -s http://localhost:8083/connectors/ticketdb-connector/status | python3 -m json.tool
