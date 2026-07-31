# `samvaad-platform`

The small set of things all three Python services need to behave identically, and
which are dangerous to implement twice.

```bash
pip install -e packages/platform
```

| Module | What it gives you | Why it is shared rather than copied |
|---|---|---|
| `logging` | JSON structured logs, request id on every line | A request traced across api → speech → genai is only traceable if all three name the field the same thing. |
| `redaction` | Field scrubbing for logs and error reports | The list of things that must never reach Sentry — transcripts, audio refs, canonical text — has to be one list. Two lists means one of them is out of date. |
| `tracing` | `RequestContextMiddleware`, `request_id()` | One header name (`X-Request-Id`), one propagation rule. |
| `errors` | `ProblemDetail` and the handler that renders it | Every service returns the same error shape, so the client has one error path rather than three. |
| `ratelimit` | Token bucket with a pluggable backend | Rate limiting that differs per service is rate limiting an attacker can shop around. |
| `security` | Service-to-service token check, security headers | See `docs/SECURITY.md`. |

## The rule this package exists to enforce

**No learner content is ever logged.** Not a transcript, not a `canonical_text`,
not an audio key, not a phrase a learner typed. `redaction.scrub` is applied by
the logging formatter itself, so the protection does not depend on every call
site remembering — which is the only way a rule like this survives six months.

Identifiers are logged. Content is not. A `user_id` in a log line is how an
incident gets diagnosed; a transcript in a log line is a data breach with a
retention policy attached.
