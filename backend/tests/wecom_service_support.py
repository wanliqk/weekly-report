"""Shared test doubles for WECOM-06 Service-level tests.

Not a `test_*.py` module itself (pytest's default discovery pattern never
collects it), imported by `test_wecom_connection_service.py` and
`test_wecom_sync_service.py`. Field values mirror
`tests/fixtures/wecom/get_template_combine_info_response.json` /
`formcol_detail_response.json` / `answer_page_response.json` so the shapes
built here stay consistent with what `WECOM-04`'s own contract tests already
verify the real `WeComInternalClient` produces — this module only replaces
the network boundary (`WeComClientLike`'s duck-typed Protocol,
`app/services/wecom_connection.py` / `app/services/wecom_sync.py`), never the
domain object shapes themselves.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.integrations.wecom.client import WeComClientError
from app.integrations.wecom.schemas import (
    WeComCookieIn,
    WeComFormDetail,
    WeComFormDetailForkItem,
    WeComQuestionItem,
    WeComSubmissionResult,
    WeComSubmitDailyPayload,
    WeComTemplateEntry,
    WeComTemplateInfo,
)

DEFAULT_FORM_ID = "SYNTHETIC-FORM-0000000000000000000fork"
DEFAULT_TEMPLATE_ID = "SYNTHETIC-TEMPLATE-0000000000000001"
DEFAULT_REPLY_VID = "9000000000000011"
DEFAULT_REPLY_NAME = "王小明"
DATE_QUESTION_ID = "1000000001"
TODAY_QUESTION_ID = "1000000002"
TOMORROW_QUESTION_ID = "1000000003"


def build_target_questions() -> list[WeComQuestionItem]:
    """Connect-time shape (`get_template_combine_info`) — still carries
    `pos`/`ext`, unlike `build_form_detail_questions()` below."""
    return [
        WeComQuestionItem(
            question_id=DATE_QUESTION_ID,
            title="日期",
            reply_type=11,
            must_reply=False,
            pos=1,
            ext={"qdata_sub_type": "date"},
        ),
        WeComQuestionItem(
            question_id=TODAY_QUESTION_ID,
            title="今日工作",
            reply_type=1,
            must_reply=True,
            pos=2,
            ext=None,
        ),
        WeComQuestionItem(
            question_id=TOMORROW_QUESTION_ID,
            title="明日计划",
            reply_type=1,
            must_reply=True,
            pos=3,
            ext=None,
        ),
    ]


def build_form_detail_questions() -> list[WeComQuestionItem]:
    """Execute-time shape (`formcol/detail`'s `question_infos[]`) — never
    carries `pos`/`ext` (both already-optional fields on `WeComQuestionItem`),
    matching what `WeComInternalClient._parse_form_detail` actually produces.
    Same `question_id`/`reply_type`/`must_reply` as `build_target_questions()`
    so a stub-driven schema-fingerprint comparison still matches by default."""
    return [
        WeComQuestionItem(
            question_id=DATE_QUESTION_ID, title="日期", reply_type=11, must_reply=False
        ),
        WeComQuestionItem(
            question_id=TODAY_QUESTION_ID, title="今日工作", reply_type=1, must_reply=True
        ),
        WeComQuestionItem(
            question_id=TOMORROW_QUESTION_ID, title="明日计划", reply_type=1, must_reply=True
        ),
    ]


def build_template_info(
    *,
    form_id: str = DEFAULT_FORM_ID,
    template_id: str = DEFAULT_TEMPLATE_ID,
    entries: list[WeComTemplateEntry] | None = None,
    questions: list[WeComQuestionItem] | None = None,
) -> WeComTemplateInfo:
    resolved_entries = (
        entries
        if entries is not None
        else [
            WeComTemplateEntry(
                journalid="SYNTHETIC-JOURNAL-0000000000000001",
                createtime=1700000000,
                reply_id=DEFAULT_REPLY_VID,
                reply_name=DEFAULT_REPLY_NAME,
                form_id=form_id,
            )
        ]
    )
    return WeComTemplateInfo(
        template_id=template_id,
        form_id=form_id,
        entries=resolved_entries,
        questions=questions if questions is not None else build_target_questions(),
    )


def build_fork_item(*, form_id: str, ctime: int, status: int = 1) -> WeComFormDetailForkItem:
    return WeComFormDetailForkItem(form_id=form_id, ctime=ctime, status=status)


def build_form_detail(
    *,
    form_id: str = DEFAULT_FORM_ID,
    creater_vid: str = DEFAULT_REPLY_VID,
    creater_name: str = DEFAULT_REPLY_NAME,
    questions: list[WeComQuestionItem] | None = None,
    fork_items: list[WeComFormDetailForkItem] | None = None,
) -> WeComFormDetail:
    return WeComFormDetail(
        form_id=form_id,
        creater_vid=creater_vid,
        creater_name=creater_name,
        questions=questions if questions is not None else build_form_detail_questions(),
        fork_items=fork_items if fork_items is not None else [],
    )


def build_submission_result(
    *,
    answer_id: str = "1",
    reply_id: str = "9000000000000012",
    journal_uuid: str = "SYNTHETIC-JOURNAL-UUID-0000000000000000000000000001",
    user_vid: str = "9000000000000012",
) -> WeComSubmissionResult:
    return WeComSubmissionResult(
        answer_id=answer_id, reply_id=reply_id, journal_uuid=journal_uuid, user_vid=user_vid
    )


class StubWeComClient:
    """Implements the `WeComClientLike` Protocol from both
    `app/services/wecom_connection.py` (`get_template_info`/`submit_daily`)
    and `app/services/wecom_sync.py` (`get_form_detail`/`submit_daily`) —
    structural typing, one stub satisfies both. Each remote call
    independently returns a fixed value or raises a fixed error; call counts
    are tracked so tests can assert a call was (or wasn't) made — e.g.
    `submit_daily` must never be invoked when a duplicate fork was found
    (`docs/方案设计.md` §10.2).
    """

    def __init__(
        self,
        *,
        template_info: WeComTemplateInfo | None = None,
        template_error: WeComClientError | None = None,
        form_detail: WeComFormDetail | None = None,
        form_detail_error: WeComClientError | None = None,
        submission_result: WeComSubmissionResult | None = None,
        submit_error: WeComClientError | None = None,
    ) -> None:
        self.template_info = template_info if template_info is not None else build_template_info()
        self.template_error = template_error
        self.form_detail = form_detail if form_detail is not None else build_form_detail()
        self.form_detail_error = form_detail_error
        self.submission_result = (
            submission_result if submission_result is not None else build_submission_result()
        )
        self.submit_error = submit_error
        self.closed = False
        self.get_template_info_calls = 0
        self.get_form_detail_calls = 0
        self.submit_daily_calls = 0

    async def get_template_info(
        self, cookie_jar: Sequence[WeComCookieIn], form_id: str
    ) -> WeComTemplateInfo:
        self.get_template_info_calls += 1
        if self.template_error is not None:
            raise self.template_error
        return self.template_info

    async def get_form_detail(
        self, cookie_jar: Sequence[WeComCookieIn], form_id: str
    ) -> WeComFormDetail:
        self.get_form_detail_calls += 1
        if self.form_detail_error is not None:
            raise self.form_detail_error
        return self.form_detail

    async def submit_daily(
        self, cookie_jar: Sequence[WeComCookieIn], payload: WeComSubmitDailyPayload
    ) -> WeComSubmissionResult:
        self.submit_daily_calls += 1
        if self.submit_error is not None:
            raise self.submit_error
        return self.submission_result

    async def aclose(self) -> None:
        self.closed = True
