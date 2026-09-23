# Extraction Roadmap

Latticery will be extracted incrementally from the Factory currently operating in ComicPile.

## Phase 0: Bootstrap

- establish standalone vocabulary and architectural boundaries;
- create a minimal Python package;
- document invariants before moving implementation;
- keep ComicPile's Factory operational throughout extraction.

## Phase 1: Pure policy

Extract deterministic policy first:

- dependency parsing and executable-work eligibility;
- stage precedence;
- worker/lease policy;
- priority and lane ranking;
- WIP limits and review backpressure;
- producer/reviewer independence;
- duplicate implementation suppression.

The goal is a pure, heavily tested policy layer with no ComicPile imports.

## Phase 2: Work-lattice model

Introduce explicit domain types for nodes, edges, workers, leases, stages, gates, evidence, capacity, and boundaries.

Existing distributed state may continue to live in GitHub initially. The model should make that state explicit without requiring a new database.

## Phase 3: GitHub adapter

Move GitHub-specific projection and mutation behind an adapter:

- issues and dependency declarations;
- pull requests and linked work;
- labels and stages;
- reviews;
- checks/CI;
- exact-head readiness;
- closing relationships;
- human-only markers.

## Phase 4: Dispatcher and completion control

Extract coordination behavior for:

- claiming work;
- lease revalidation;
- dispatch/refill;
- completion draining;
- free-entry capacity;
- independent workflow/concurrency boundaries;
- recovery from stale or interrupted claims.

## Phase 5: Worker runtime contract

Define the smallest contract between Latticery and an executor:

- assignment input;
- bounded context;
- progress/evidence publication;
- retry and recovery semantics;
- completion/release.

The contract must permit different agent CLIs, models, or human workers.

## Phase 6: ComicPile consumes Latticery

Replace copied behavior in ComicPile with the standalone package or CLI behind compatibility adapters. Migrate incrementally and compare decisions during the transition.

## Phase 7: Generalize deliberately

Only after the first extraction is stable should Latticery generalize beyond GitHub-centric software delivery. New abstractions must be justified by a second concrete use case rather than anticipated in advance.

## Migration rule

**Do not pause the working Factory to perform a big-bang rewrite.** Extract one proven behavior at a time, preserve tests, and keep the originating system shippable.
