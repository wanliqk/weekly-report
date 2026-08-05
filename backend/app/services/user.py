def normalize_username(username: str) -> str:
    """The single normalization rule behind `uq_users_username_normalized`.

    Shared by bootstrap and (later) admin-driven user creation so both
    paths agree on what counts as a duplicate username.
    """
    return username.strip().casefold()
