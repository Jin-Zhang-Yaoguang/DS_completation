# V14 panel seal v2 invalidation

- Status: invalidated before candidate sealing and before any environment game.
- Candidate archives sealed under this seal: no.
- Screen games started: no.
- Confirmatory games started: no.
- Test outcome accessed: no.
- Trigger: a concurrent V14 development run wrote another result file on already quarantined V13 screen seeds. The v2 verifier correctly stopped because its evidence-file closure changed, although the exposure union and both panel hashes were unchanged.
- Repair: the replacement verifier keeps the frozen ledger immutable, rescans current evidence before every run, and fails only when current evidence intersects a selected screen/confirmatory source. Harmless duplicate evidence on already quarantined seeds is reported as drift without changing the panel.
