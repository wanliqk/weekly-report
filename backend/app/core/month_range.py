from datetime import date

from app.core.errors import AppError


class InvalidMonthError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40001, http_status=400, message="month 必须是 YYYY-MM 格式")


def parse_month_range(month: str) -> tuple[date, date]:
    """Parses a `YYYY-MM` string into its first and last calendar date."""
    year_text, _, month_text = month.partition("-")
    try:
        year, month_no = int(year_text), int(month_text)
        month_start = date(year, month_no, 1)
        # December of `date.MAXYEAR` has no following month to compute
        # `next_month_start` from; also raises ValueError, caught below.
        next_month_start = date(year + 1, 1, 1) if month_no == 12 else date(year, month_no + 1, 1)
    except ValueError as error:
        raise InvalidMonthError() from error
    month_end = date.fromordinal(next_month_start.toordinal() - 1)
    return month_start, month_end
