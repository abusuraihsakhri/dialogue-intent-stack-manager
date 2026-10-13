# Dialogue Intent Stack Manager

A small, local-first tool for tracking nested dialogue goals, suspending an earlier goal during an interruption, and resuming it afterward. The repository also retains its existing illustrative, threshold-based task-audit utilities.

## Features

- **Browser intent stack:** push an intent, suspend the previous intent, complete the current task, and resume the suspended task.
- **Snapshot exchange:** export or import versioned JSON snapshots. The browser validates snapshots before restoring them.
- **Audit preview:** evaluate the existing threshold rules directly in JavaScript without a server. These values are illustrative and are **not clinical decision rules**.
- **Python API:** FastAPI serves the same browser page, a server-side signed-audit endpoint, an audit trail endpoint, and Prometheus text metrics.
- **Python stack library:** `intent_stack.stack.IntentStack` provides bounded push/pop, snapshots, and validated restoration.

The browser preview and server audit are distinct: **browser previews are unsigned**. The server's HMAC-SHA256 entries are stored only in memory and cannot attest to entries across restarts unless the application also persists the log externally (not implemented here).

## Use in a browser

Open `web/index.html` directly for the fully local, dependency-free interface. Push intents and complete them to return to the previous goal. Export a snapshot as JSON for manual backup and import it later. Data remains in the current tab until exported; closing the page loses unsaved state.

GitHub Pages deployment is defined in `.github/workflows/pages.yml`. Publishing depends on Pages being enabled for this repository and on a successful deployment workflow.

## Run the Python service

Requires Python 3.10+ (package metadata currently permits Python 3.9+) and pip:

```bash
python -m pip install -e '.[dev]'
python cli.py serve --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` for the interface. Choose **Local FastAPI server** in the audit form to send evaluations to `POST /api/audit`. Interactive API documentation is at `/docs`.

The original command-line tools are retained:

```bash
python cli.py audit --task-id TASK-01 --target KEY-01 --primary 20 --secondary 5
python cli.py batch --input sample.csv --output results.csv
python cli.py verify-audit
python -m intent_stack.cli audit --task-id TASK-01
```

The `intent_stack` legacy CLI and the `agents` API implement different historical thresholds. Do not assume the two produce identical audit classifications. The browser preview follows the `agents` API rules (primary above 25; secondary above 12; and status keywords).

### Python intent stack

```python
from intent_stack.stack import IntentStack

stack = IntentStack()
stack.push("Write manuscript", {"section": "Introduction"})
stack.push("Check citation")
stack.pop()  # Resumes "Write manuscript"
snapshot = stack.snapshot()
```

The stack is local to its Python instance. It is not a persistent multi-user conversation service.

## Security and privacy

The browser interface makes no requests while using its local stack and audit-preview mode. Server audit mode sends the supplied form values to the selected same-origin FastAPI server. Avoid entering real patient data, secrets, or other sensitive identifiers.

The Python service uses regular-expression screening for some identifier patterns, but it does **not** provide comprehensive PHI detection or HIPAA compliance. The audit trail is tamper-evident only for the current in-memory process and secret key. Configure a strong, private `AUDIT_SECRET_KEY` for reproducible verification within the service; never commit it. The Compose file requires this environment variable.

## Testing

```bash
python -m pip install -e '.[dev]'
pytest -q
python -m compileall -q agents intent_stack cli.py enrichment.py simulator.py
```

GitHub Actions tests Python 3.10, 3.11, and 3.12. The browser requires a current JavaScript-capable desktop or mobile browser; no Python runtime or Pyodide download is needed.

## Technology and license

Python, FastAPI, Pydantic, standard-library HMAC/SHA-256 and vanilla HTML/CSS/JavaScript. [MIT License](LICENSE).
