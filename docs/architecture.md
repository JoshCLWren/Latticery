# Architecture

Latticery models autonomous software delivery as a persistent graph rather than as a single long-running agent conversation.

## System model

The **work lattice** contains durable work state and the relationships that determine what may happen next. Workers repeatedly inspect the lattice, acquire a lease on an eligible action, execute bounded work, publish durable evidence, and release control.

A worker loop can be summarized as:

```text
inspect → select → lease → execute → publish evidence → release
                         ↘ recover ↗
```

The system surrounding those loops is graph-shaped:

```text
issue/dependency graph
        ↓
 executable work
   ↙          ↘
implement    review
   ↓          ↓
 change ← requested changes
   ↓
verification gates
   ↓
ready / human boundary / merge
```

## Architectural layers

### 1. Domain

Pure representations and policies for:

- work nodes and dependency edges
- worker identity and capabilities
- leases
- stages
- gates and evidence
- eligibility
- priority
- capacity and backpressure
- recovery state
- human boundaries

Domain policy should be deterministic and testable without GitHub, an LLM, or a running worker.

### 2. Coordinator

The coordinator projects external state into the domain model and decides the next eligible actions. It must tolerate concurrent workers and stale observations. Any mutation that depends on ownership or capacity must revalidate those assumptions at the mutation boundary.

### 3. Worker runtime

Workers execute bounded actions. Latticery should not require one model vendor or one agent harness. A worker is replaceable as long as it can consume an assignment and publish the evidence required by the lattice.

### 4. Adapters

Adapters translate real systems into Latticery concepts. The first extraction is GitHub-oriented because the originating Factory uses issues, pull requests, reviews, labels, checks, and Actions as durable coordination state.

Application-specific conventions belong here rather than in the domain.

### 5. Control plane

Dispatch, completion draining, refill, and recovery cooperate to keep capacity productive. No single worker or work item should monopolize the system.

## Correctness properties

Latticery should preserve these invariants:

- blocked work is never selected as executable;
- a live lease prevents duplicate execution of the same next action;
- an open implementation change suppresses duplicate implementation;
- a producer cannot satisfy its own independent-review requirement;
- requested changes may return work to its producer for repair;
- stage precedence is deterministic;
- readiness applies to an exact revision, and a changed revision invalidates stale readiness;
- capacity is rechecked before mutations that consume capacity;
- waiting on external review or CI need not consume an execution worker;
- human-only boundaries cannot be crossed by automation.

## Initial extraction boundary

The first implementation will be extracted from ComicPile's proven Factory behavior. Names, paths, labels, and product policy from ComicPile are not automatically Latticery primitives. Each extracted behavior must answer:

1. Is this a generic coordination invariant?
2. Is this GitHub adapter behavior?
3. Is this worker-runtime behavior?
4. Is this ComicPile policy that should remain outside Latticery?

That classification is the guardrail against turning Latticery into ComicPile with the serial numbers filed off.
