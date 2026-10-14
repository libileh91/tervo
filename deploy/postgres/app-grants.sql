-- Run as the administrator after every successful Alembic migration.
-- No default table grants: the API never receives access to alembic_version.
\getenv app_role TERVO_DB_USER

BEGIN;
SELECT format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE %I.%I TO %I',
              schemaname, tablename, :'app_role')
FROM pg_tables
WHERE schemaname = 'public' AND tablename <> 'alembic_version'
\gexec
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO :"app_role";
REVOKE ALL ON TABLE public.alembic_version FROM :"app_role";
COMMIT;
