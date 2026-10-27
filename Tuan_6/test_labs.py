import base64
import io
import json
import secrets
import tempfile
import threading
import time
import tokenize
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import jwt
import yaml
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate

import lab1_basic
import lab2_api_key
import lab3_jwt
import lab4_rbac
import social_api
from database import create_user, get_db


PASSWORD = "test-only-passphrase"


class AppCase(unittest.TestCase):
    factory = None

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config = {
            "TESTING": True,
            "DATABASE": str(Path(self.directory.name) / "test.sqlite3"),
            "JWT_SECRET_KEY": secrets.token_hex(32),
            "BCRYPT_ROUNDS": 4,
            "AUTH_RATE_LIMIT": 1000,
        }
        self.app = self.factory(self.config)
        self.client = self.app.test_client()
        with self.app.app_context():
            connection = get_db()
            for email, role in [
                ("an@vnu.edu.vn", "editor"),
                ("binh@vnu.edu.vn", "viewer"),
                ("admin@vnu.edu.vn", "admin"),
                ("manager@vnu.edu.vn", "manager"),
            ]:
                user_id = create_user(email, PASSWORD, role)
                connection.execute(
                    "INSERT INTO orders (owner_id, item, quantity) VALUES (?, ?, ?)", (user_id, "SOA", 1)
                )
                for visibility in ("public", "private"):
                    connection.execute(
                        "INSERT INTO posts (owner_id, title, content, visibility) VALUES (?, ?, ?, ?)",
                        (user_id, "SOA", "Authentication", visibility),
                    )
            connection.commit()

    def basic(self, email="an@vnu.edu.vn", password=PASSWORD):
        encoded = base64.b64encode(f"{email}:{password}".encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    def bearer(self, token):
        return {"Authorization": f"Bearer {token}"}

    def login(self, email="an@vnu.edu.vn", prefix="/api/auth"):
        response = self.client.post(f"{prefix}/login", json={"email": email, "password": PASSWORD})
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()

    def sql(self, statement, parameters=()):
        with self.app.app_context():
            connection = get_db()
            connection.execute(statement, parameters)
            connection.commit()

    def signed(self, token, updates=None, remove=()):
        claims = jwt.decode(token, self.config["JWT_SECRET_KEY"], algorithms=["HS256"],
                            options={"verify_aud": False})
        claims.update(updates or {})
        for name in remove:
            claims.pop(name, None)
        return jwt.encode(claims, self.config["JWT_SECRET_KEY"], algorithm="HS256")


class BasicTests(AppCase):
    factory = staticmethod(lab1_basic.create_app)

    def test_missing_and_wrong_credentials_challenge(self):
        for headers in ({}, self.basic(password="wrong"), self.basic(email="unknown@example.com")):
            response = self.client.get("/api/orders", headers=headers)
            self.assertEqual(response.status_code, 401)
            self.assertIn('Basic realm="orders"', response.headers["WWW-Authenticate"])

    def test_success_returns_principal_and_only_owned_orders(self):
        response = self.client.get("/api/orders", headers=self.basic())
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["principal"], "an@vnu.edu.vn")
        self.assertEqual([order["owner_id"] for order in data["orders"]], [1])
        self.assertNotIn("password", response.get_data(as_text=True))

    def test_password_is_bcrypt_hash_with_individual_salt(self):
        with self.app.app_context():
            rows = get_db().execute("SELECT password_hash FROM users").fetchall()
            self.assertTrue(all(row[0].startswith(b"$2b$") for row in rows))
            self.assertEqual(len({row[0] for row in rows}), 4)
            self.assertNotIn(PASSWORD.encode(), [row[0] for row in rows])

    def test_disabled_user_and_long_password_fail(self):
        self.sql("UPDATE users SET active = 0 WHERE id = 1")
        self.assertEqual(self.client.get("/api/orders", headers=self.basic()).status_code, 401)
        self.assertEqual(self.client.get("/api/orders", headers=self.basic(password="x" * 73)).status_code, 401)

    def test_sql_injection_does_not_authenticate(self):
        response = self.client.get("/api/orders", headers=self.basic(email="' OR 1=1 --"))
        self.assertEqual(response.status_code, 401)

    def test_rate_limit_uses_ip_across_accounts(self):
        self.app.config["AUTH_RATE_LIMIT"] = 2
        for email in ("first@example.com", "second@example.com"):
            self.assertEqual(self.client.get("/api/orders", headers=self.basic(email=email)).status_code, 401)
        response = self.client.get("/api/orders", headers=self.basic())
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response.headers["Retry-After"]), 0)


class ApiKeyTests(AppCase):
    factory = staticmethod(lab2_api_key.create_app)

    def mint(self, email="an@vnu.edu.vn", **fields):
        data = {"scopes": ["orders:read"], **fields}
        response = self.client.post("/api/keys", headers=self.basic(email=email), json=data)
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()

    def test_key_is_shown_once_and_database_stores_only_hash(self):
        result = self.mint()
        raw = result["api_key"]
        self.assertTrue(raw.startswith("sk_live_"))
        response = self.client.get("/api/keys", headers=self.basic())
        self.assertNotIn(raw, response.get_data(as_text=True))
        self.assertNotIn("hash", response.get_data(as_text=True))
        with self.app.app_context():
            row = dict(get_db().execute("SELECT * FROM api_keys").fetchone())
            self.assertEqual(len(row["hash"]), 64)
            self.assertNotIn(raw, str(row))

    def test_missing_invalid_and_query_string_key_rejected(self):
        raw = self.mint()["api_key"]
        for path, headers in [
            ("/api/orders", {}),
            ("/api/orders", {"X-Api-Key": "invalid"}),
            (f"/api/orders?api_key={raw}", {}),
        ]:
            self.assertEqual(self.client.get(path, headers=headers).status_code, 401)

    def test_valid_key_reads_owned_orders_and_blocks_bola(self):
        headers = {"X-Api-Key": self.mint()["api_key"]}
        response = self.client.get("/api/orders", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r["owner_id"] for r in response.get_json()["orders"]], [1])
        self.assertEqual(self.client.get("/api/orders/2", headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/orders/999", headers=headers).status_code, 404)

    def test_read_only_key_cannot_write(self):
        response = self.client.post("/api/orders", headers={"X-Api-Key": self.mint()["api_key"]},
                                    json={"item": "SOA", "quantity": 2})
        self.assertEqual(response.status_code, 403)

    def test_write_key_cannot_assign_other_owner(self):
        headers = {"X-Api-Key": self.mint(scopes=["orders:write"])["api_key"]}
        self.assertEqual(self.client.post("/api/orders", headers=headers,
                         json={"item": "SOA", "quantity": 2, "owner_id": 2}).status_code, 400)
        response = self.client.post("/api/orders", headers=headers, json={"item": "SOA", "quantity": 2})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["owner_id"], 1)

    def test_cannot_mint_more_privilege_than_owner(self):
        response = self.client.post("/api/keys", headers=self.basic(email="binh@vnu.edu.vn"),
                                    json={"scopes": ["orders:write"]})
        self.assertEqual(response.status_code, 403)

    def test_expired_and_revoked_keys_rejected(self):
        result = self.mint()
        headers = {"X-Api-Key": result["api_key"]}
        self.sql("UPDATE api_keys SET expires_at = ? WHERE id = ?", (int(time.time()) - 1, result["key"]["id"]))
        self.assertEqual(self.client.get("/api/orders", headers=headers).status_code, 401)
        result = self.mint()
        response = self.client.delete(f"/api/keys/{result['key']['id']}", headers=self.basic())
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get("/api/orders", headers={"X-Api-Key": result["api_key"]}).status_code, 401)

    def test_rotation_invalidates_old_key(self):
        original = self.mint()
        response = self.client.post(f"/api/keys/{original['key']['id']}/rotate", headers=self.basic())
        self.assertEqual(response.status_code, 201)
        rotated = response.get_json()
        self.assertNotEqual(rotated["api_key"], original["api_key"])
        self.assertEqual(self.client.get("/api/orders", headers={"X-Api-Key": original["api_key"]}).status_code, 401)
        self.assertEqual(self.client.get("/api/orders", headers={"X-Api-Key": rotated["api_key"]}).status_code, 200)

    def test_other_user_cannot_manage_key(self):
        key_id = self.mint()["key"]["id"]
        headers = self.basic(email="binh@vnu.edu.vn")
        self.assertEqual(self.client.get(f"/api/keys/{key_id}", headers=headers).status_code, 403)
        self.assertEqual(self.client.delete(f"/api/keys/{key_id}", headers=headers).status_code, 403)
        self.assertEqual(self.client.post(f"/api/keys/{key_id}/rotate", headers=headers).status_code, 403)

    def test_ip_allowlist_and_forwarded_ip_spoof(self):
        result = self.mint(ip_allowlist=["192.0.2.0/24"])
        headers = {"X-Api-Key": result["api_key"], "X-Forwarded-For": "192.0.2.1"}
        self.assertEqual(self.client.get("/api/orders", headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/orders", headers=headers,
                         environ_overrides={"REMOTE_ADDR": "192.0.2.1"}).status_code, 200)

    def test_key_rechecks_owner_scopes_and_account_status(self):
        headers = {"X-Api-Key": self.mint()["api_key"]}
        self.sql("UPDATE users SET scopes = '[]' WHERE id = 1")
        self.assertEqual(self.client.get("/api/orders", headers=headers).status_code, 403)
        self.sql("UPDATE users SET active = 0 WHERE id = 1")
        self.assertEqual(self.client.get("/api/orders", headers=headers).status_code, 401)

    def test_invalid_key_options_are_rejected(self):
        for data in [
            {"scopes": "orders:read"}, {"scopes": []}, {"scopes": [False]},
            {"scopes": ["orders:read"], "expires_in": True},
            {"scopes": ["orders:read"], "ip_allowlist": ["invalid"]},
            {"scopes": ["orders:read"], "owner_id": 2},
        ]:
            with self.subTest(data=data):
                self.assertEqual(self.client.post("/api/keys", headers=self.basic(), json=data).status_code, 400)


class JwtTests(AppCase):
    factory = staticmethod(lab3_jwt.create_app)

    def test_login_and_protected_route(self):
        tokens = self.login()
        self.assertEqual(tokens["token_type"], "Bearer")
        self.assertTrue(899 <= tokens["expires_in"] <= 900)
        response = self.client.get("/api/orders", headers=self.bearer(tokens["access_token"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["orders"][0]["owner_id"], 1)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        me = self.client.get("/api/me", headers=self.bearer(tokens["access_token"]))
        self.assertNotIn("password_hash", me.get_data(as_text=True))

    def test_invalid_credentials_have_same_response(self):
        responses = [self.client.post("/api/auth/login", json={"email": email, "password": "wrong"})
                     for email in ("an@vnu.edu.vn", "missing@example.com")]
        self.assertTrue(all(r.status_code == 401 for r in responses))
        self.assertEqual(responses[0].get_json(), responses[1].get_json())

    def test_missing_malformed_and_tampered_tokens_rejected(self):
        token = self.login()["access_token"]
        parts = token.split(".")
        parts[1] = base64.urlsafe_b64encode(b'{"sub":"3","role":"admin"}').decode().rstrip("=")
        for headers in ({}, self.bearer("not-a-token"), self.bearer(".".join(parts))):
            self.assertEqual(self.client.get("/api/orders", headers=headers).status_code, 401)

    def test_none_algorithm_and_wrong_signature_rejected(self):
        token = self.login()["access_token"]
        claims = jwt.decode(token, options={"verify_signature": False})
        for invalid in [jwt.encode(claims, key="", algorithm="none"),
                        jwt.encode(claims, secrets.token_hex(32), algorithm="HS256")]:
            self.assertEqual(self.client.get("/api/orders", headers=self.bearer(invalid)).status_code, 401)

    def test_expiry_issuer_audience_and_required_claims(self):
        token = self.login()["access_token"]
        invalid = [
            self.signed(token, {"exp": int(time.time()) - 1}),
            self.signed(token, {"iss": "other-issuer"}),
            self.signed(token, {"aud": "other-service"}),
            self.signed(token, remove=("exp",)),
            self.signed(token, remove=("iat",)),
            self.signed(token, remove=("jti",)),
            self.signed(token, {"scopes": [123]}),
        ]
        for value in invalid:
            self.assertEqual(self.client.get("/api/orders", headers=self.bearer(value)).status_code, 401)

    def test_access_and_refresh_cannot_be_swapped(self):
        tokens = self.login()
        self.assertEqual(self.client.get("/api/orders", headers=self.bearer(tokens["refresh_token"])).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/refresh", headers=self.bearer(tokens["access_token"])).status_code, 401)

    def test_refresh_rotates_without_extending_session(self):
        original = self.login()
        response = self.client.post("/api/auth/refresh", headers=self.bearer(original["refresh_token"]))
        self.assertEqual(response.status_code, 200)
        rotated = response.get_json()
        self.assertNotEqual(rotated["refresh_token"], original["refresh_token"])
        old = jwt.decode(original["refresh_token"], options={"verify_signature": False})
        new = jwt.decode(rotated["refresh_token"], options={"verify_signature": False})
        self.assertEqual(new["exp"], old["exp"])
        self.assertEqual(self.client.get("/api/orders", headers=self.bearer(rotated["access_token"])).status_code, 200)

    def test_refresh_replay_revokes_entire_family(self):
        original = self.login()
        rotated = self.client.post("/api/auth/refresh", headers=self.bearer(original["refresh_token"])).get_json()
        self.assertEqual(self.client.post("/api/auth/refresh", headers=self.bearer(original["refresh_token"])).status_code, 401)
        for token in (original["access_token"], rotated["access_token"]):
            self.assertEqual(self.client.get("/api/orders", headers=self.bearer(token)).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/refresh", headers=self.bearer(rotated["refresh_token"])).status_code, 401)

    def test_concurrent_refresh_allows_one_rotation(self):
        original = self.login()
        barrier = threading.Barrier(2)

        def refresh():
            with self.app.test_client() as client:
                barrier.wait(timeout=5)
                response = client.post("/api/auth/refresh", headers=self.bearer(original["refresh_token"]))
                return response.status_code, response.get_json()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: refresh(), range(2)))
        self.assertEqual(sorted(status for status, data in results), [200, 401])
        rotated = next(data for status, data in results if status == 200)
        self.assertEqual(self.client.get("/api/orders", headers=self.bearer(rotated["access_token"])).status_code, 401)

    def test_logout_revokes_access_and_refresh_persistently(self):
        tokens = self.login()
        self.assertEqual(self.client.post("/api/auth/logout", headers=self.bearer(tokens["access_token"])).status_code, 204)
        restarted = self.factory(self.config).test_client()
        self.assertEqual(restarted.get("/api/orders", headers=self.bearer(tokens["access_token"])).status_code, 401)
        self.assertEqual(restarted.post("/api/auth/refresh", headers=self.bearer(tokens["refresh_token"])).status_code, 401)

    def test_expired_session_and_disabled_user_rejected(self):
        tokens = self.login()
        self.sql("UPDATE sessions SET expires_at = ?", (int(time.time()) - 1,))
        self.assertEqual(self.client.get("/api/orders", headers=self.bearer(tokens["access_token"])).status_code, 401)
        tokens = self.login()
        self.sql("UPDATE users SET active = 0 WHERE id = 1")
        self.assertEqual(self.client.get("/api/orders", headers=self.bearer(tokens["access_token"])).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/refresh", headers=self.bearer(tokens["refresh_token"])).status_code, 401)

    def test_scope_removal_is_immediate_and_refresh_reloads_permissions(self):
        tokens = self.login()
        self.sql("UPDATE users SET scopes = ? WHERE id = 1", (json.dumps(["posts:read"]),))
        self.assertEqual(self.client.get("/api/orders", headers=self.bearer(tokens["access_token"])).status_code, 403)
        response = self.client.post("/api/auth/refresh", headers=self.bearer(tokens["refresh_token"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["scope"], "posts:read")

    def test_login_validation_blocks_mass_assignment(self):
        for body in [None, [], {}, {"email": 1, "password": PASSWORD},
                     {"email": "an@vnu.edu.vn", "password": "x" * 73},
                     {"email": "an@vnu.edu.vn", "password": PASSWORD, "roles": ["admin"]}]:
            response = self.client.post("/api/auth/login", data=json.dumps(body), content_type="application/json")
            self.assertEqual(response.status_code, 400)

    def test_content_type_malformed_json_and_body_limit(self):
        self.assertEqual(self.client.post("/api/auth/login", data="plain").status_code, 415)
        self.assertEqual(self.client.post("/api/auth/login", data="{", content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post("/api/auth/login", json={"email": "x" * 17000, "password": PASSWORD}).status_code, 413)

    def test_rate_limit_uses_account_across_ips(self):
        self.app.config["AUTH_RATE_LIMIT"] = 2
        for ip in ("192.0.2.1", "192.0.2.2"):
            response = self.client.post("/api/auth/login", json={"email": "an@vnu.edu.vn", "password": "wrong"},
                                        environ_overrides={"REMOTE_ADDR": ip})
            self.assertEqual(response.status_code, 401)
        response = self.client.post("/api/auth/login", json={"email": "an@vnu.edu.vn", "password": PASSWORD},
                                    environ_overrides={"REMOTE_ADDR": "192.0.2.3"})
        self.assertEqual(response.status_code, 429)

    def test_weak_signing_secret_refused(self):
        with self.assertRaises(RuntimeError):
            self.factory({**self.config, "JWT_SECRET_KEY": "weak"})


class RbacTests(AppCase):
    factory = staticmethod(lab4_rbac.create_app)

    def test_owner_allowed_other_user_forbidden_admin_allowed(self):
        for email, expected in [("an@vnu.edu.vn", 200), ("binh@vnu.edu.vn", 403), ("admin@vnu.edu.vn", 200)]:
            tokens = self.login(email)
            self.assertEqual(self.client.get("/api/orders/1", headers=self.bearer(tokens["access_token"])).status_code, expected)

    def test_viewer_cannot_call_admin_or_create_order(self):
        headers = self.bearer(self.login("binh@vnu.edu.vn")["access_token"])
        self.assertEqual(self.client.get("/api/admin/users", headers=headers).status_code, 403)
        self.assertEqual(self.client.post("/api/orders", headers=headers, json={"item": "SOA", "quantity": 1}).status_code, 403)

    def test_admin_users_response_does_not_expose_password_hashes(self):
        response = self.client.get("/api/admin/users", headers=self.bearer(self.login("admin@vnu.edu.vn")["access_token"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()["users"]), 4)
        self.assertNotIn("password", response.get_data(as_text=True))

    def test_delete_requires_admin_or_manager_and_all_scopes(self):
        editor = self.bearer(self.login()["access_token"])
        self.assertEqual(self.client.delete("/api/orders/1", headers=editor).status_code, 403)
        manager = self.login("manager@vnu.edu.vn")["access_token"]
        restricted = self.signed(manager, {"scopes": ["orders:write"]})
        self.assertEqual(self.client.delete("/api/orders/4", headers=self.bearer(restricted)).status_code, 403)
        self.assertEqual(self.client.delete("/api/orders/1", headers=self.bearer(manager)).status_code, 403)
        self.assertEqual(self.client.delete("/api/orders/4", headers=self.bearer(manager)).status_code, 204)
        self.assertEqual(self.client.get("/api/orders/4", headers=self.bearer(manager)).status_code, 404)

    def test_admin_bypass_does_not_bypass_scope(self):
        token = self.login("admin@vnu.edu.vn")["access_token"]
        limited = self.signed(token, {"scopes": ["posts:read"]})
        self.assertEqual(self.client.get("/api/orders/1", headers=self.bearer(limited)).status_code, 403)
        self.assertEqual(self.client.delete("/api/orders/1", headers=self.bearer(token)).status_code, 204)

    def test_role_change_is_effective_before_token_expiry(self):
        token = self.login("admin@vnu.edu.vn")["access_token"]
        self.sql("UPDATE users SET role = 'viewer' WHERE id = 3")
        self.assertEqual(self.client.get("/api/admin/users", headers=self.bearer(token)).status_code, 403)

    def test_create_rejects_owner_injection_and_invalid_quantity(self):
        headers = self.bearer(self.login()["access_token"])
        for data in [{"item": "SOA", "quantity": 1, "owner_id": 2}, {"item": "SOA", "quantity": True},
                     {"item": "SOA", "quantity": 0}]:
            self.assertEqual(self.client.post("/api/orders", headers=headers, json=data).status_code, 400)
        response = self.client.post("/api/orders", headers=headers, json={"item": "SOA", "quantity": 2})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["owner_id"], 1)


class SocialTests(AppCase):
    factory = staticmethod(social_api.create_app)

    def setUp(self):
        super().setUp()
        self.spec = yaml.safe_load(Path(__file__).with_name("openapi.yaml").read_text())

    def social_token(self, email="an@vnu.edu.vn"):
        return self.login(email, prefix="/auth")["access_token"]

    def validate_response(self, path, method, response):
        response_spec = self.spec["paths"][path][method]["responses"][str(response.status_code)]
        if "$ref" in response_spec:
            response_spec = self.spec["components"]["responses"][response_spec["$ref"].split("/")[-1]]
        schema = {"$defs": self.spec["components"]["schemas"],
                  **response_spec["content"]["application/json"]["schema"]}
        if "$ref" in schema:
            schema["$ref"] = schema["$ref"].replace("#/components/schemas/", "#/$defs/")
        Draft202012Validator(schema).validate(response.get_json())

    def test_openapi_valid_and_describes_exact_required_paths_and_scopes(self):
        validate(self.spec)
        self.assertEqual(set(self.spec["paths"]), {"/auth/login", "/auth/refresh", "/posts/{id}"})
        self.assertEqual(self.spec["paths"]["/posts/{id}"]["get"]["x-required-scopes"], ["posts:read"])
        routes = {rule.rule for rule in self.app.url_map.iter_rules() if rule.endpoint != "static"}
        self.assertEqual(routes, {"/auth/login", "/auth/refresh", "/posts/<id>"})

    def test_public_private_and_admin_access_match_spec(self):
        for email, path, status in [
            ("an@vnu.edu.vn", "/posts/1", 200), ("binh@vnu.edu.vn", "/posts/1", 200),
            ("an@vnu.edu.vn", "/posts/2", 200), ("binh@vnu.edu.vn", "/posts/2", 403),
            ("admin@vnu.edu.vn", "/posts/2", 200), ("an@vnu.edu.vn", "/posts/999", 404),
            ("an@vnu.edu.vn", "/posts/invalid", 400), ("an@vnu.edu.vn", "/posts/0", 400),
            ("an@vnu.edu.vn", "/posts/9999999999999999999", 400),
        ]:
            with self.subTest(email=email, path=path):
                response = self.client.get(path, headers=self.bearer(self.social_token(email)))
                self.assertEqual(response.status_code, status)
                self.validate_response("/posts/{id}", "get", response)

    def test_token_missing_scope_and_wrong_type_match_spec(self):
        missing = self.client.get("/posts/1")
        self.assertEqual(missing.status_code, 401)
        self.validate_response("/posts/{id}", "get", missing)
        token = self.social_token()
        limited = self.signed(token, {"scopes": ["orders:read"]})
        response = self.client.get("/posts/1", headers=self.bearer(limited))
        self.assertEqual(response.status_code, 403)
        self.validate_response("/posts/{id}", "get", response)
        refresh = self.login(prefix="/auth")["refresh_token"]
        self.assertEqual(self.client.get("/posts/1", headers=self.bearer(refresh)).status_code, 401)

    def test_login_and_refresh_response_schemas(self):
        response = self.client.post("/auth/login", json={"email": "an@vnu.edu.vn", "password": PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.validate_response("/auth/login", "post", response)
        headers = self.bearer(response.get_json()["refresh_token"])
        response = self.client.post("/auth/refresh", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.validate_response("/auth/refresh", "post", response)
        replay = self.client.post("/auth/refresh", headers=headers)
        self.assertEqual(replay.status_code, 401)
        self.validate_response("/auth/refresh", "post", replay)

    def test_login_errors_match_spec(self):
        cases = [
            self.client.post("/auth/login", json={}),
            self.client.post("/auth/login", json={"email": "an@vnu.edu.vn", "password": "wrong"}),
            self.client.post("/auth/login", json={"email": "x" * 17000, "password": PASSWORD}),
            self.client.post("/auth/login", data="text"),
        ]
        self.assertEqual([r.status_code for r in cases], [400, 401, 413, 415])
        for response in cases:
            self.validate_response("/auth/login", "post", response)
        self.app.config["AUTH_RATE_LIMIT"] = 1
        response = self.client.post("/auth/login", json={"email": "an@vnu.edu.vn", "password": PASSWORD})
        self.assertEqual(response.status_code, 429)
        self.validate_response("/auth/login", "post", response)

    def test_token_cannot_be_reused_for_other_lab_audience(self):
        token = self.social_token()
        config = {**self.config, "DATABASE": str(Path(self.directory.name) / "lab3.sqlite3")}
        other = lab3_jwt.create_app(config).test_client()
        self.assertEqual(other.get("/api/orders", headers=self.bearer(token)).status_code, 401)


class SourceAndCliTests(unittest.TestCase):
    def test_python_sources_have_no_comments(self):
        for path in Path(__file__).parent.glob("*.py"):
            tokens = tokenize.generate_tokens(io.StringIO(path.read_text()).readline)
            self.assertFalse(any(token.type == tokenize.COMMENT for token in tokens), path.name)

    def test_cli_seeds_each_app_without_overwriting_existing_data(self):
        for factory in (lab1_basic.create_app, lab2_api_key.create_app, lab3_jwt.create_app,
                        lab4_rbac.create_app, social_api.create_app):
            with self.subTest(factory=factory.__module__), tempfile.TemporaryDirectory() as directory:
                app = factory({"TESTING": True, "DATABASE": str(Path(directory) / "cli.sqlite3"),
                               "BCRYPT_ROUNDS": 4, "JWT_SECRET_KEY": secrets.token_hex(32)})
                runner = app.test_cli_runner()
                result = runner.invoke(args=["init-demo"], input=f"{PASSWORD}\n{PASSWORD}\n")
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertIn("admin@vnu.edu.vn: admin", result.output)
                repeated = runner.invoke(args=["init-demo"], input=f"{PASSWORD}\n{PASSWORD}\n")
                self.assertNotEqual(repeated.exit_code, 0)
                self.assertIn("không ghi đè", repeated.output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
