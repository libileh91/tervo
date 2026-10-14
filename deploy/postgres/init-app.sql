-- Fresh volumes only. The official entrypoint skips this on an existing PGDATA.
-- Read credentials from the container environment, never from CLI arguments.
\getenv app_role TERVO_DB_USER
\getenv app_password TERVO_DB_PASSWORD
\getenv db_name POSTGRES_DB

BEGIN;
CREATE ROLE :"app_role" LOGIN PASSWORD :'app_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
REVOKE ALL ON DATABASE :"db_name" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"db_name" TO :"app_role";
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO :"app_role";
COMMIT;
