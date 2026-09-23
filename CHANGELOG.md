# Changelog

## 0.8.1 - Unreleased

- Fix the Windows `install-plugin.ps1 -Update` path for marketplaces registered
  from a local clone. It refreshes the plugin from the registered local root;
  Git-backed marketplaces still run `marketplace upgrade` first.

## 0.8.0 - 2026-09-22

- Move primary, demanding implementation, and fresh review to GPT-6 Sol / xhigh;
  move bounded implementation to GPT-6 Luna / max. Retire Terra as an active lane.
- Add optional GPT-6 Astra / high decision advice, excluded from default installation
  and requiring explicit per-decision consultation authorization. No automatic review
  or implementation by Astra; no claim of a hard spending cap.
- Separate implementation difficulty, consequence risk, and delegation benefit.
  Keep solo/delegate/audit/full, with bounded provisional discovery before confirmation.
- Add declared-plan validation and expected-runtime-role checks; distinguish Sol
  implementer from Sol reviewer and keep the `sol` check alias for review compatibility.
- Use one versioned role registry and one Python 3.11+ companion implementation on
  POSIX and native Windows. POSIX installation now requires Python 3.11+ too.
- Migrate exact v0.7.0 profiles; retain prior historical fingerprints and CRLF fixtures.
  Archive known Terra outside discovery; preserve personalized profiles with warnings.
- Extend portable and Windows tests, document authorization/isolation limitations,
  rollback, live model smoke tests, and cost-per-accepted-change evaluation.

## 0.7.0 - 2026-09-22

Published checkpoint at `30e185a3509e5b8cc651a367708caa65a1d76283`: GPT-5.6 selective
routing, Sol / xhigh, Luna / max, Terra / max, native Windows support, and safe migration
of historical v0.6.0 CRLF profiles. This release/tag is not changed by the GPT-6 work.
