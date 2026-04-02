# Test Suite Follow-Ups

Track these for a separate branch so the current test-strengthening work stays scoped.

## Filename Decoupling

- Replace remaining exact-filename adapter assumptions where they are not part of the real export contract.
- Review `MetaMask state logs.json` handling and support profile-based discovery instead of one hard-coded filename.
- Review `activities-export` and Coinbase statement-name matching so adapters can prefer header/family detection over filename substrings when that is safe.
- Review non-chain-scoped EVM explorer captures, where scope and owned-address detection still rely on filename hints when the folder itself is not chain-scoped.

## Fixture Migration

- Continue moving repo-backed "unit" coverage onto purpose-built fixtures until only true integration and e2e tests depend on checked-in exports.
- Split the largest repo-data adapter tests into smaller fixture-backed cases that isolate one rule or exception at a time.

## Execution Profiles

- Add a documented CI-oriented command set for `pytest -m "not slow"` and full repo-data coverage so the fast loop and full verification loop stay explicit.
