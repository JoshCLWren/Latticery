# Contributing to Latticery

Latticery is in early extraction from a working autonomous software-delivery system.

## Principles for changes

- Prefer explicit invariants over clever orchestration.
- Keep domain policy deterministic and side-effect free where practical.
- Put provider-specific behavior behind adapters.
- Treat concurrency, stale observations, retries, and interruption as normal operating conditions.
- Require durable evidence for state transitions.
- Preserve human-controlled boundaries.
- Avoid abstractions that are not supported by a concrete use case.

## Development

The package currently targets Python 3.11+.

```bash
python -m pip install -e ".[dev]"
pytest
```

## Pull requests

A change should explain:

1. which lattice behavior or invariant it changes;
2. why that behavior belongs in Latticery rather than a host adapter;
3. how concurrency or recovery affects it, when applicable;
4. which tests demonstrate the intended behavior.

Small extraction PRs are preferred over wholesale ports from ComicPile.
