-- REVIEW ONLY. Run as a database administrator in a DISPOSABLE clone first.
-- Existing logins and ownership are deliberately not changed by this migration.
BEGIN;
CREATE ROLE wp_migrator NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE ROLE wp_runtime NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
-- Function owner only, never grant membership to an application/login role.
CREATE ROLE wp_authenticator NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE SCHEMA wp_security AUTHORIZATION wp_migrator;
REVOKE ALL ON SCHEMA wp_security FROM PUBLIC;
GRANT USAGE ON SCHEMA public, wp_security TO wp_runtime, wp_authenticator;
GRANT SELECT (token_hash, user_id, expires_at) ON public.sessions TO wp_authenticator;
GRANT SELECT (id, role) ON public.users TO wp_authenticator;
-- pg_catalog.sha256 is built in: no extension, signing key or arbitrary actor ID.
-- The bearer is a capability. Knowing a stored hash does NOT reproduce it.
CREATE FUNCTION wp_security.actor_id() RETURNS bigint
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE result bigint;
BEGIN
 SELECT s.user_id INTO result FROM public.sessions s
 WHERE s.token_hash = encode(sha256(convert_to(
   nullif(current_setting('wiejskapaka.bearer', true), ''), 'UTF8')), 'hex')
 AND s.expires_at::timestamptz > statement_timestamp();
 RETURN result;
END $$;
CREATE FUNCTION wp_security.actor_role() RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog AS $$
 SELECT u.role::text FROM public.users u WHERE u.id = wp_security.actor_id()
$$;
-- New function owners need CREATE only during ownership transfer.
GRANT CREATE ON SCHEMA wp_security TO wp_authenticator;
ALTER FUNCTION wp_security.actor_id() OWNER TO wp_authenticator;
ALTER FUNCTION wp_security.actor_role() OWNER TO wp_authenticator;
REVOKE CREATE ON SCHEMA wp_security FROM wp_authenticator;
REVOKE ALL ON FUNCTION wp_security.actor_id(), wp_security.actor_role() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION wp_security.actor_id(), wp_security.actor_role() TO wp_runtime, wp_authenticator;
COMMIT;
