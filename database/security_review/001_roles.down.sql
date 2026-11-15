BEGIN;
DROP SCHEMA wp_security CASCADE;
REVOKE SELECT (token_hash, user_id, expires_at) ON public.sessions FROM wp_authenticator;
REVOKE SELECT (id, role) ON public.users FROM wp_authenticator;
REVOKE USAGE ON SCHEMA public FROM wp_runtime, wp_authenticator;
DROP ROLE wp_authenticator;
DROP ROLE wp_runtime;
DROP ROLE wp_migrator;
COMMIT;
