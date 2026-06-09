# Siosa's Library

**Path of Exile 1** wiki Q&A — live [poewiki.net](https://www.poewiki.net) retrieval, cited answers, optional multi-step planning.

**Demo** [poesiosa.net](https://www.poesiosa.net/) · **Docs** [Architecture](docs/architecture.html) · [Changelog](docs/changelog.html) · [Deploy](DEPLOY.md)

## How it works

```mermaid
flowchart TB
  subgraph agentic["Multi-step planning — when needed"]
    PL[Planner adds short search terms]
  end
  subgraph pass["One live retrieval pass"]
    Q[Your question]
    F[Fuse queries]
    S[Search poewiki]
    T[Title probes]
    O[Re-order hits by overlap]
    DL[Download pages]
    C[Chunk]
    RR[Rerank]
    FT[Optional tangential filter]
    OUT[Top excerpts → LLM]
  end
  PL -.-> F
  Q --> F --> S
  F --> T
  S --> O
  T --> O
  O --> DL --> C --> RR --> FT --> OUT
```

**Interactive pipeline** (hover steps, alternatives): [Architecture](docs/architecture.html#pipeline-overview).

**Developer setup** → [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/LAPTOP_SETUP.md](docs/LAPTOP_SETUP.md).

## License

Source code: [MIT](LICENSE). Game artwork in `web/public/art assets/` is **not** MIT-licensed — see [NOTICE](NOTICE). Not affiliated with Grinding Gear Games.
