#!/bin/sh
set -eu
app_password="$(cat /run/secrets/db_password)"
psql -v ON_ERROR_STOP=1 --username postgres --dbname supplyflow --set=app_password="$app_password" <<'SQL'
CREATE ROLE supplyflow LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'app_password';
ALTER DATABASE supplyflow OWNER TO supplyflow;
GRANT ALL ON SCHEMA public TO supplyflow;
SQL
