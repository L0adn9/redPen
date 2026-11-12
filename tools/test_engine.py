#!/usr/bin/env python3
"""Offline tests for the RedPen audit engine (no API calls, no credits).

    python3 tools/test_engine.py            # all offline tests
    python3 tools/test_engine.py --live     # also one real audit + key check (uses ~7 API calls)
"""
import io
import json
import os
import pathlib
import sys
import time
import unittest
import urllib.error
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import redpen_audit as ra  # noqa: E402
from check_verdict import check  # noqa: E402

DEMO = ra.load_demo("DSA201_A1")["steps"]


def http_error(code, body="{}"):
    return urllib.error.HTTPError("https://x", code, "err", {}, io.BytesIO(body.encode()))


def fake_post_from_demo(steps=DEMO):
    """A stand-in for _post that answers each agent with the saved output for that agent."""
    by_system = {ra.instructions("01-intake.md"): "01-intake", ra.instructions("05-examiner.md"): "05-examiner"}
    for p, f in ra.PERSONAS.items():
        by_system[ra.instructions(f)] = f"02-{p}"

    def post(model, system, user, key):
        name = by_system.get(system, "06-verdict")
        return json.dumps(steps[name]), model
    return post


class Env(unittest.TestCase):
    def setUp(self):
        self._env = mock.patch.dict(os.environ, {"REDPEN_BACKEND": "openrouter", "OPENROUTER_API_KEY": "sk-or-test",
                                                 "REDPEN_MODELS": "google/gemini-3-flash-preview"}, clear=False)
        self._env.start()
        self._sleep = mock.patch.object(ra.time, "sleep", lambda s: None)
        self._sleep.start()

    def tearDown(self):
        self._sleep.stop()
        self._env.stop()


class TestModelsAndKeys(Env):
    def test_gemini_only_guard(self):
        with mock.patch.dict(os.environ, {"REDPEN_MODELS": "openai/gpt-5"}):
            self.assertRaises(ra.AuditError, ra.models)
        with mock.patch.dict(os.environ, {"REDPEN_MODELS": "anthropic/gemini-fake"}):
            self.assertRaises(ra.AuditError, ra.models)
        self.assertRaises(ra.AuditError, ra.call, "s", "u", "k", ["meta/llama"])

    def test_bare_names_get_google_prefix_on_openrouter(self):
        with mock.patch.dict(os.environ, {"REDPEN_MODELS": "gemini-4-argon, google/gemini-3.8-flash"}):
            self.assertEqual(ra.models(), ["google/gemini-4-argon", "google/gemini-3.8-flash"])

    def test_gemini_backend_strips_prefix(self):
        with mock.patch.dict(os.environ, {"REDPEN_BACKEND": "gemini", "REDPEN_MODELS": "google/gemini-3.8-flash"}):
            self.assertEqual(ra.models(), ["gemini-3.8-flash"])

    def test_set_credentials_detects_backend(self):
        ra.set_credentials("sk-or-v1-abc")
        self.assertEqual((ra.backend(), ra.api_key()), ("openrouter", "sk-or-v1-abc"))
        ra.set_credentials("AIzaFakeKey")
        self.assertEqual((ra.backend(), ra.api_key()), ("gemini", "AIzaFakeKey"))

    def test_missing_key_is_a_clear_error(self):
        with mock.patch.dict(os.environ, {"REDPEN_BACKEND": "gemini", "GEMINI_API_KEY": ""}), \
                mock.patch.object(ra, "ROOT", pathlib.Path("/nonexistent")):
            with self.assertRaises(ra.AuditError) as c:
                ra.api_key()
            self.assertIn("GEMINI_API_KEY", str(c.exception))

    def test_label_for(self):
        self.assertEqual(ra.label_for(["google/gemini-4-argon"]), "pro")
        self.assertEqual(ra.label_for(["google/gemini-3.1-pro-preview"]), "pro")
        self.assertEqual(ra.label_for(["google/gemini-3-flash-preview"]), "flash")


class TestCall(Env):
    def test_bad_key_fails_fast(self):
        t0 = time.time()
        with mock.patch.object(ra, "_post", side_effect=http_error(401)):
            with self.assertRaises(ra.AuditError) as c:
                ra.call("s", "u", "k", ["google/gemini-3-flash-preview", "google/gemini-3.8-flash"])
        self.assertIn("rejected", str(c.exception))
        self.assertLess(time.time() - t0, 1)

    def test_no_credit_fails_fast(self):
        with mock.patch.object(ra, "_post", side_effect=http_error(402)):
            with self.assertRaises(ra.AuditError) as c:
                ra.call("s", "u", "k")
            self.assertIn("credit", str(c.exception))

    def test_quota_moves_to_next_model(self):
        calls = []

        def post(model, s, u, k):
            calls.append(model)
            if model.endswith("a"):
                raise http_error(429)
            return '{"ok": true}', model
        with mock.patch.object(ra, "_post", side_effect=post):
            out = ra.call("s", "u", "k", ["google/gemini-a", "google/gemini-b"])
        self.assertEqual(out, ('{"ok": true}', "google/gemini-b"))
        self.assertEqual(calls, ["google/gemini-a", "google/gemini-b"])

    def test_timeout_moves_to_next_model(self):
        def post(model, s, u, k):
            if model.endswith("a"):
                raise TimeoutError("read timed out")
            return "{}", model
        with mock.patch.object(ra, "_post", side_effect=post):
            self.assertEqual(ra.call("s", "u", "k", ["google/gemini-a", "google/gemini-b"])[1], "google/gemini-b")

    def test_garbled_response_becomes_audit_error(self):
        with mock.patch.object(ra, "_post", side_effect=ValueError("Expecting value")):
            self.assertRaises(ra.AuditError, ra.call, "s", "u", "k")

    def test_server_error_retries_then_succeeds(self):
        seq = [http_error(503), http_error(503), ("{}", "m")]

        def post(*a):
            x = seq.pop(0)
            if isinstance(x, Exception):
                raise x
            return x
        with mock.patch.object(ra, "_post", side_effect=post):
            self.assertEqual(ra.call("s", "u", "k"), ("{}", "m"))

    def test_all_quota_gives_one_clear_error(self):
        with mock.patch.object(ra, "_post", side_effect=http_error(429)):
            with self.assertRaises(ra.AuditError) as c:
                ra.call("s", "u", "k", ["google/gemini-a"])
            self.assertIn("quota", str(c.exception))


class TestParse(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(ra.parse('{"a": 1}', "x"), ({"a": 1}, None))

    def test_fenced(self):
        data, warn = ra.parse('```json\n{"a": 1}\n```', "x")
        self.assertEqual(data, {"a": 1})
        self.assertIn("fences", warn)

    def test_repeated_object(self):
        data, warn = ra.parse('{"a": 1}{"a": 1}', "x")
        self.assertEqual(data, {"a": 1})
        self.assertIn("extra text", warn)

    def test_control_chars_allowed(self):
        self.assertEqual(ra.parse('{"a": "line1\nline2"}', "x")[0]["a"], "line1\nline2")

    def test_garbage(self):
        self.assertRaises(ra.AuditError, ra.parse, "Sorry, I can't help", "x")


class TestRunAudit(Env):
    def test_full_chain_matches_contract(self):
        seen = []
        with mock.patch.object(ra, "_post", side_effect=fake_post_from_demo()):
            r = ra.run_audit("brief", "rubric", "clo", "DSA201", "A1", lecturer_email="lec@apu.edu.my",
                             run_date="2026-11-13", on_step=lambda n, d, s: seen.append(n))
        v = r["verdict"]
        self.assertEqual(check(v)[0], [])
        self.assertEqual(v["model"], "flash")
        self.assertEqual(v["audit_date"], "2026-11-13")
        self.assertEqual(v["lecturer_email"], "lec@apu.edu.my")
        self.assertEqual(v["file_name"], "DSA201_A1_flash_20261113.json")
        self.assertEqual(seen[0], "01-intake")
        self.assertEqual(sorted(seen[1:4]), ["02-copy_paster", "02-honest_helper", "02-prompt_engineer"])
        self.assertEqual(seen[4:], ["05-examiner", "06-verdict"])
        self.assertTrue(r["log"]["contract"]["ok"])

    def test_pro_label_from_model(self):
        with mock.patch.dict(os.environ, {"REDPEN_MODELS": "google/gemini-4-argon"}), \
                mock.patch.object(ra, "_post", side_effect=fake_post_from_demo()):
            self.assertEqual(ra.run_audit("b", "r", "c", "DSA201", "A1")["verdict"]["model"], "pro")

    def test_wrong_exposure_is_corrected(self):
        steps = json.loads(json.dumps(DEMO))
        steps["06-verdict"]["exposure"] = "LOW"  # copy-paster passed, so the rule says HIGH
        with mock.patch.object(ra, "_post", side_effect=fake_post_from_demo(steps)):
            r = ra.run_audit("b", "r", "c", "DSA201", "A1")
        self.assertEqual(r["verdict"]["exposure"], "HIGH")
        self.assertTrue(any("corrected" in w for w in r["log"]["warnings"]))

    def test_broken_json_retried_once(self):
        good = fake_post_from_demo()
        state = {"n": 0}

        def post(model, system, user, key):
            state["n"] += 1
            if state["n"] == 1:
                return "not json", model
            return good(model, system, user, key)
        with mock.patch.object(ra, "_post", side_effect=post):
            r = ra.run_audit("b", "r", "c", "DSA201", "A1")
        self.assertEqual(r["verdict"]["exposure"], "HIGH")

    def test_empty_inputs_rejected(self):
        self.assertRaises(ra.AuditError, ra.run_audit, "", "rubric", "")
        self.assertRaises(ra.AuditError, ra.run_audit, "brief", "   ", "")

    def test_failure_is_audit_error(self):
        with mock.patch.object(ra, "_post", side_effect=http_error(401)):
            self.assertRaises(ra.AuditError, ra.run_audit, "b", "r", "c")


class TestSavedRuns(unittest.TestCase):
    def test_every_saved_run_is_valid(self):
        names = ra.demo_runs()
        self.assertGreaterEqual(len(names), 9)
        for n in names:
            r = ra.load_demo(n)
            self.assertEqual(check(r["verdict"])[0], [], n)
            v = r["verdict"]
            self.assertEqual(v["exposure"], ra.expected_exposure(v["persona_totals"], v["pass_mark"]), n)
            for k in ("01-intake", "02-copy_paster", "02-prompt_engineer", "02-honest_helper", "05-examiner"):
                self.assertIn(k, r["steps"], n)

    def test_prompts_extract(self):
        for f in ["01-intake.md", "05-examiner.md", "06-verdict.md", *ra.PERSONAS.values()]:
            self.assertGreater(len(ra.instructions(f)), 200, f)


class TestGeminiEnterpriseReadiness(Env):
    """The pass-through mode = Gemini Enterprise worst case, where a step only sees the previous step."""

    def fake_passthrough_post(self, drift=False):
        rules = ra.passthrough_rules()
        intake = DEMO["01-intake"]

        def post(model, system, user, key):
            if system == ra.instructions("01-intake.md"):
                return json.dumps(intake), model
            for p, f in ra.PERSONAS.items():
                if system.startswith(ra.instructions(f)):
                    self.assertIn(rules[f"02-{p}"], system)
                    inp = json.loads(user)
                    bundle = {"intake": inp.get("intake", inp), "attempts": dict(inp.get("attempts", {}))}
                    if drift:
                        bundle["intake"] = dict(bundle["intake"], module="CHANGED")
                    bundle["attempts"][p] = DEMO[f"02-{p}"]["answers"]
                    return json.dumps(bundle), model
            if system.startswith(ra.instructions("05-examiner.md")):
                inp = json.loads(user)
                self.assertEqual(sorted(inp["attempts"]), sorted(ra.PERSONAS))  # all three arrived via the bundle
                return json.dumps({"meta": {"module": "DSA201"}, "examiner": DEMO["05-examiner"]}), model
            self.assertIn(rules["06-verdict"], system)
            self.assertIn('"meta"', user)
            return json.dumps(DEMO["06-verdict"]), model
        return post

    def test_passthrough_chain(self):
        order = []
        with mock.patch.object(ra, "_post", side_effect=self.fake_passthrough_post()):
            r = ra.run_audit("b", "r", "c", "DSA201", "A1", mode="passthrough", on_step=lambda n, d, s: order.append(n))
        self.assertEqual(order, ["01-intake", "02-copy_paster", "02-prompt_engineer", "02-honest_helper",
                                 "05-examiner", "06-verdict"])  # strictly sequential, like the canvas
        self.assertTrue(r["log"]["contract"]["ok"])
        self.assertEqual(r["steps"]["02-honest_helper"]["answers"], DEMO["02-honest_helper"]["answers"])

    def test_passthrough_copy_drift_is_reported(self):
        with mock.patch.object(ra, "_post", side_effect=self.fake_passthrough_post(drift=True)):
            r = ra.run_audit("b", "r", "c", "DSA201", "A1", mode="passthrough")
        self.assertTrue(any("copy drift" in w for w in r["log"]["warnings"]))

    def test_passthrough_rules_found(self):
        self.assertEqual(sorted(ra.passthrough_rules()), ["02-copy_paster", "02-honest_helper", "02-prompt_engineer",
                                                          "05-examiner", "06-verdict"])

    def test_schemas_accept_every_saved_output(self):
        for n in ra.demo_runs():
            for step, data in ra.load_demo(n)["steps"].items():
                self.assertEqual(ra.schema_errors(step, data), [], f"{n} {step}")

    def test_schema_catches_wrong_shape(self):
        self.assertTrue(ra.schema_errors("06-verdict", {"exposure": "VERY HIGH"}))
        self.assertTrue(ra.schema_errors("02-copy_paster", {"persona": "x", "answers": "not a list"}))

    def test_wrong_shape_is_retried(self):
        good = fake_post_from_demo()
        state = {"n": 0}

        def post(model, system, user, key):
            state["n"] += 1
            if state["n"] == 1:
                return json.dumps({"module": "X"}), model  # valid JSON, wrong shape for Intake
            return good(model, system, user, key)
        with mock.patch.object(ra, "_post", side_effect=post):
            r = ra.run_audit("b", "r", "c", "DSA201", "A1")
        self.assertEqual(r["steps"]["01-intake"], DEMO["01-intake"])


def live():
    print("\n--- live: key check")
    for m, s in ra.check_models():
        print(f"  {m}: {s}")
    print("--- live: one full audit (DSA201 A1)")
    d = ROOT / "data" / "sample-assessments" / "DSA201" / "A1"
    t0 = time.time()
    r = ra.run_audit(*(d.joinpath(n).read_text() for n in ("brief.txt", "rubric.txt", "clo-map.txt")),
                     "DSA201", "A1", lecturer_email="lecturer@example.edu",
                     on_step=lambda n, _, s: print(f"  {n}: {s}s"))
    v = r["verdict"]
    print(f"  exposure={v['exposure']} totals={v['persona_totals']} contract={r['log']['contract']} "
          f"warnings={r['log']['warnings']} {time.time() - t0:.0f}s")
    assert r["log"]["contract"]["ok"], "contract failed"


if __name__ == "__main__":
    want_live = "--live" in sys.argv
    sys.argv = [a for a in sys.argv if a != "--live"]
    result = unittest.main(exit=False, verbosity=1).result
    if want_live and result.wasSuccessful():
        live()
    sys.exit(0 if result.wasSuccessful() else 1)
