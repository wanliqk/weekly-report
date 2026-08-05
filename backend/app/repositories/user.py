from sqlalchemy import func, insert, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def any_exists(self) -> bool:
        result = await self._session.execute(select(func.count()).select_from(User))
        return result.scalar_one() > 0

    async def create_if_no_users_exist(self, user: User) -> bool:
        """Insert `user` iff the `users` table is currently empty, atomically.

        A plain "check row count, then insert" is racy: two concurrent
        bootstrap requests can both observe zero rows before either writes.
        Folding the check into the insert itself as `INSERT ... SELECT ...
        WHERE NOT EXISTS (...)` closes the gap for free: SQLite only ever
        lets one connection hold the write lock needed to execute this
        statement, so a second concurrent caller either blocks (up to
        `busy_timeout`) until the first commits — and then correctly sees
        the table as non-empty and inserts zero rows — or, if it runs
        first, wins outright. Two concurrent bootstrap attempts can never
        both succeed.
        """
        stmt = insert(User).from_select(
            [
                "id",
                "username",
                "username_normalized",
                "display_name",
                "password_hash",
                "role",
                "password_changed_at",
            ],
            select(
                literal(user.id),
                literal(user.username),
                literal(user.username_normalized),
                literal(user.display_name),
                literal(user.password_hash),
                literal(user.role),
                literal(user.password_changed_at),
            ).where(~select(User.id).exists()),
        )
        result = await self._session.execute(stmt)
        return bool(result.rowcount == 1)
