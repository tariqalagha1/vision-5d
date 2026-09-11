# Risk Report — V5D-PASCAL-SCHEMA-CONFORMANCE-001

## Core Risks
| Risk | Severity | Status |
|---|---|---|
| Pascal pre-1.0 API breaking changes | MEDIUM | Pin to commit 42ac4be1 |
| coordinate projection precision in wall-local conversion | LOW | Reversible via wall geometry |
| REST API unavailable in production | MEDIUM | Fall back to direct @pascal-app/core import |
| Bun requirement vs Node toolchain | LOW | Pascal supports Node >= 18 |

## Integration Risks
- Scene persistence format may change before Pascal 1.0
- MCP server is a separate package — version skew possible
- SQLite scene store may need migration for large scenes

## Verdict
**PROCEED WITH VERSION PINNING AND ISOLATED MODULE**
