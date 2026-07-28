# Documentation

This directory holds two kinds of documentation, kept apart on purpose
(see [ADR 0030](decisions/adrs/0030-separate-public-and-developer-documentation.md)).

- **Using environment packs** → [`public/`](public/index.md). Only this directory
  is published to the documentation site, its search index, and its sitemap.
- **Working on this repository** → [`README.md`](README.md), the developer index:
  the decision records, CI, and release mechanics.

Adding a page under `public/` publishes it. A record anywhere else stays in the
repository and is never published.
