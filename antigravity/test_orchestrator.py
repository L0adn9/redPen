"""Offline tests for the RedPen orchestrator (no API key needed).   Run:  ../.venv/bin/python test_orchestrator.py"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import orchestrator as o

CCP = o.ROOT / "data" / "pilot-real" / "CCP" / "A1"
WAPP = o.ROOT / "data" / "pilot-real" / "WAPP" / "GA"


def run(backend, folder=CCP, module="CT074-3-2", assessment="A1"):
    out = Path(tempfile.mkdtemp(prefix="redpen-test-"))
    orch = o.Orchestrator(backend, module, assessment, o.read_folder(folder), out, log=lambda *_: None)
    return orch, orch.run(), out


class Tampered(o.ReplayBackend):
    """Replays a saved run but changes what one agent says, to test the orchestrator's checks."""

    def __init__(self, saved, agent_id, change, times=99):
        super().__init__(saved)
        self.agent_id, self.change, self.left = agent_id, change, times

    def call(self, agent, system, user, attempt):
        text, model = super().call(agent, system, user, attempt)
        if agent["id"] == self.agent_id and self.left > 0:
            self.left -= 1
            return self.change(text), model
        return text, model


class TestOrchestrator(unittest.TestCase):
    def test_every_agent_has_a_prompt_and_schema(self):
        for a in o.AGENTS:
            self.assertGreater(len(o.prompt_of(a)), 200, a["id"])
            self.assertTrue((o.SCHEMAS / a["schema"]).exists(), a["schema"])

    def test_waves_run_personas_in_parallel_and_redesign_last(self):
        orch, v, out = run(o.ReplayBackend("CCP_A1"))
        self.assertEqual(orch.trace["waves"], [["01-intake"], ["02-copy_paster", "02-prompt_engineer", "02-honest_helper"],
                                               ["05-examiner"], ["06-verdict"], ["07-redesign"]])
        self.assertEqual(v["exposure"], "HIGH")
        for f in ("trace.json", "report.md", "07-redesign.json"):
            self.assertTrue((out / f).exists(), f)
        self.assertIn("waiting for the lecturer", json.loads((out / "trace.json").read_text())["approval"]["status"])
        shutil.rmtree(out)

    def test_low_exposure_skips_redesign(self):
        orch, v, out = run(o.ReplayBackend("WAPP_GA"), WAPP, "CT050-3-2-WAPP", "GA")
        self.assertEqual(v["exposure"], "LOW")
        self.assertIn("07-redesign", orch.trace["skipped"])
        self.assertFalse((out / "07-redesign.json").exists())
        shutil.rmtree(out)

    def test_guardrail_corrects_a_wrong_exposure(self):
        def lie(text):
            d = json.loads(text)
            d["exposure"] = "LOW"
            return json.dumps(d)
        orch, v, out = run(Tampered("CCP_A1", "06-verdict", lie))
        self.assertEqual(v["exposure"], "HIGH")
        self.assertIn("corrected", orch.trace["guardrails"][0])
        shutil.rmtree(out)

    def test_agent_corrects_itself_after_a_rejected_output(self):
        orch, v, out = run(Tampered("CCP_A1", "05-examiner", lambda t: '{"not": "the examiner format"}', times=1))
        t = orch.trace["agents"]["05-examiner"]
        self.assertEqual(t["attempts"], 2)
        self.assertTrue(t["schema_ok"])
        shutil.rmtree(out)

    def test_swarm_mode_contract(self):
        """Swarm workers fetch input, submit output; bad output is rejected; Examiner waits for all three students."""
        import contextlib, io, sys as _sys
        D = o.DEMO_RUNS / "CCP_A1"

        def cli(*args):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                try:
                    rc = o.main(list(args))
                except SystemExit as e:
                    rc = e.code
            return rc, buf.getvalue()

        rc, out = cli("swarm-init", str(CCP), "--module", "CT074-3-2", "--assessment", "A1")
        run = out.split("RUN=")[1].split()[0]
        try:
            self.assertEqual(cli("input", run, "examiner")[0], 1)  # must wait
            bad = o.HERE / run / "drafts" / "bad.json"
            bad.write_text('{"x": 1}')
            self.assertEqual(cli("submit", run, "intake", str(bad))[0], 2)  # rejected
            for agent, f in [("intake", "01-intake"), ("copy-paster", "02-copy_paster"),
                             ("prompt-engineer", "02-prompt_engineer"), ("honest-helper", "02-honest_helper"),
                             ("examiner", "05-examiner"), ("verdict", "06-verdict"), ("redesign", "07-redesign")]:
                self.assertEqual(cli("input", run, agent)[0], 0, agent)
                rc, out = cli("submit", run, agent, str(D / f"{f}.json"))
                self.assertEqual(rc, 0, out)
            self.assertIn("run is complete", out)
            self.assertEqual(cli("finish", run)[0], 0)
            tr = json.loads((o.HERE / run / "trace.json").read_text())
            self.assertEqual(tr["agents"]["01-intake"]["attempts"], 2)
            self.assertEqual(len(tr["waves"]), 5)
            self.assertIn("passed", tr["guardrails"][0])
        finally:
            shutil.rmtree(o.HERE / run, ignore_errors=True)

    def test_live_openrouter_path_with_model_fallback(self):
        """The real HTTP code path, against a local fake OpenRouter: the first Gemini model always returns HTTP 500,
        so every agent must fall back to the second model and the run must still finish with a verdict."""
        import http.server, threading
        D = o.DEMO_RUNS / "CCP_A1"
        prompts = {a["id"]: o.prompt_of(a)[:300] for a in o.AGENTS}
        calls = []

        class Fake(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                calls.append(body["model"])
                if body["model"] == "google/broken-model":
                    self.send_response(500); self.end_headers(); self.wfile.write(b"overloaded"); return
                system = body["messages"][0]["content"]
                agent = next(i for i, p in prompts.items() if system.startswith(p[:200]))
                out = {"model": body["model"], "choices": [{"message": {"content": (D / f"{agent}.json").read_text()}}]}
                data = json.dumps(out).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(data)

        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        old_api = o.OPENROUTER_API
        o.OPENROUTER_API = f"http://127.0.0.1:{srv.server_address[1]}/api/v1/chat/completions"
        os_env = dict(o.os.environ)
        try:
            o.os.environ["OPENROUTER_API_KEY"] = "test"
            o.os.environ["AG_OPENROUTER_MODELS"] = "x"  # keep the list below instead of the app's
            b = o.OpenRouterBackend()
            b.models = ["google/broken-model", "google/gemini-3-flash-preview"]
            orch, v, out = run(b)
            self.assertEqual(v["exposure"], "HIGH")
            self.assertEqual(len(orch.trace["agents"]), 7)
            self.assertTrue(all(a["model"] == "google/gemini-3-flash-preview" for a in orch.trace["agents"].values()))
            self.assertIn("google/broken-model", calls)
            shutil.rmtree(out)
        finally:
            o.OPENROUTER_API = old_api
            o.os.environ.clear(); o.os.environ.update(os_env)
            srv.shutdown()

    def test_expected_exposure_rule(self):
        self.assertEqual(o.expected_exposure({"copy_paster": 50, "prompt_engineer": 90}, 50), "HIGH")
        self.assertEqual(o.expected_exposure({"copy_paster": 49, "prompt_engineer": 50}, 50), "MEDIUM")
        self.assertEqual(o.expected_exposure({"copy_paster": 10, "prompt_engineer": 20}, 50), "LOW")


if __name__ == "__main__":
    unittest.main(verbosity=2)
