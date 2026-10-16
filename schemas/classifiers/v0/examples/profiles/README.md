# Agent interface profile examples

These are synthetic declarations for schema and graph conformance, not qualified
harness profiles. Every `example:` pin is illustrative; no resolvable external
contract or actual capability is claimed. Production adopters must supply trusted,
immutable pins and applicability evidence.

- `resident-proxy.json`: distinct socket and standard-stream hops, a resident
  execution that can both reconnect and resume, and proxy receipt separate from
  native start/completion.
- `bounded-resume.json`: a terminating invocation can restore durable context;
  no delivery signals or reconciliation are claimed.
- `cooperative-observation.json`: a cursor commit is distinct from activation and
  execution. Unknown protocol composition is represented explicitly; this example
  cannot satisfy a policy requiring a known wire binding. The synthetic ack-binding
  pin would need to specify the exact adopted agent-wait message revision and
  registration/outcome/retention semantics in a real catalog.

The [standard](../../../../../docs/standards/agent-interface-profiles.md) defines
semantics and the consumer's required authority, evidence and pin checks.
