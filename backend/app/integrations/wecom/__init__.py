"""WeCom internal-protocol HTTP client (`WECOM-04`, `docs/方案设计.md` §8).

Pure protocol layer only: no Service, Router, or ORM access lives here. See
`client.py` for `WeComInternalClient` and its six error types, and
`schemas.py` for the request/response DTOs.
"""
