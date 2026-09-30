# V14 panel seal v1 invalidation

- Status: invalidated before candidate sealing and before any environment game.
- Candidate archives sealed under this seal: no.
- Screen games started: no.
- Confirmatory games started: no.
- Test outcome accessed: no.
- Reason: package-mode security tests exposed a local-import compatibility defect. The defect affected test invocation only, not source selection; all v1 generated artifacts were moved here before the import shim was added and before a replacement seal was generated.
