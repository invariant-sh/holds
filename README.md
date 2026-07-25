# Holds

**Task evaluation harness for LLM agents.**

Holds answers: did the agent actually solve the job? Maul proves resilience under failure; Holds measures task correctness and quality.

```text
Agent  →  Maul (chaos)  →  Holds (eval)  →  Vigil (production)
```

> Status: private / early scaffold. Implementation landing next.

## Related

Part of the [Invariant](https://github.com/invariant-sh) tooling family:

| Tool | Role |
|---|---|
| **[Maul](https://github.com/invariant-sh/maul)** | Adversarial proxy — prove resilience under failure |
| **Holds** (this repo) | Eval harness — did the agent solve the job? |
| **Vigil** | Production controls — enforce policy at the edge |

## License

Licensed under the [Apache License, Version 2.0](./LICENSE).
