# Atlas 12-minute demo script

1. Start with the problem: chat answers are not enterprise research because they are neither durable nor auditable.
2. Ask a panelist for an unseen research question and enter it into Atlas.
3. Show the planner, OpenAlex retrieval, extraction and synthesis trace while the run executes.
4. Open evidence findings and source links. Explain that source confidence is visible and degraded retrieval produces no invented conclusion.
5. Refresh the page and select the saved session in persistent memory.
6. Open `/docs` to show the versioned FastAPI contract; then show the SQLite data volume in Docker.
7. Close with the scale plan: background workers, Postgres, Qdrant hybrid retrieval and tenant-level access controls keep the same source/finding/run-event contract.
