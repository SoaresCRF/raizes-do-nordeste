#!/bin/sh
# Roda só na primeira subida do volume (docker-entrypoint-initdb.d).
# A aplicação usa um papel próprio, dono dos bancos, sem privilégios de administrador.
set -e

psql -v ON_ERROR_STOP=1 -v usuario="$BANCO_APP_USUARIO" -v senha="$BANCO_APP_SENHA" --username "$POSTGRES_USER" --dbname postgres <<-EOSQL
	CREATE ROLE :"usuario" LOGIN PASSWORD :'senha'
		NOSUPERUSER NOCREATEDB NOCREATEROLE;
	CREATE DATABASE raizes OWNER :"usuario";
	CREATE DATABASE raizes_teste OWNER :"usuario";
EOSQL
