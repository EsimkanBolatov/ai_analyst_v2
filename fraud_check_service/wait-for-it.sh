#!/bin/sh
# Взят с: https://github.com/vishnubob/wait-for-it

set -e

hostport=$1

host=$(echo $hostport | cut -d: -f1)
port=$(echo $hostport | cut -d: -f2)

until nc -z -v -w30 $host $port; do
  echo "Ожидание доступности PostgreSQL ($host:$port)..."
  sleep 1
done

echo "PostgreSQL готов! (Скрипт wait-for-it.sh завершает работу)"
