# docs

For a polished, standalone narrative (the kind you'd hand a hiring manager or instructor), read
[project-report.md](project-report.md) instead of working through the list below.

For the ~10 minute engineering-oriented tour, read in this order:

1. [architecture.md](architecture.md) — the pipeline, why each component exists, folder structure
2. [system-design.md](system-design.md) — the "why" behind every major decision (why FastAPI, why
   ResNet-50, why Grad-CAM, why Postgres, how this would scale to multiple models)
3. [api.md](api.md) — every endpoint, real request/response shapes, every status code
4. [database.md](database.md) — schema, ER diagram, what's deliberately *not* a table
5. [model.md](model.md) — dataset → preprocessing → training → validation → checkpoint → inference
6. [deployment.md](deployment.md) — Docker/Compose/CI, real bugs hit deploying it
7. [known-limitations.md](known-limitations.md) — honest gaps, not hidden ones
8. [roadmap.md](roadmap.md) — the actual branch-by-branch build history
9. [contributing.md](contributing.md) — branching model

`images/` holds the architecture, sequence, component, deployment, and ER diagrams referenced
throughout the docs above.
