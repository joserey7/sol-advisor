# Immutable migration fixtures

Exact historical profile text from v0.7.0 (`30e185a3509e5b8cc651a367708caa65a1d76283`):
- v0.2.0, v0.5.0 and v0.6.0 literals were moved from the former `verify.sh` fixtures.
- v0.6.0 CRLF strings preserve the Windows variants recognized by v0.7.0.
- v0.7.0 profiles were checked against Git blob IDs from the released tree.

Do not normalize or rewrite fixture contents during a model migration. New current
profiles with CRLF are still conflicts; this list is not a normalization rule.
