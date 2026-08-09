"""Shared test doubles for WECOM-06 Service-level tests.

Not a `test_*.py` module itself (pytest's default discovery pattern never
collects it), imported by `test_wecom_connection_service.py` and
`test_wecom_sync_service.py`. Field values mirror
`tests/fixtures/wecom/get_template_combine_info_response.json` /
`get_journal_list_response.json` / `answer_page_response.json` so the shapes
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
    WeComJournalEntry,
    WeComJournalPage,
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


def build_journal_entry(
    *,
    journalid: str,
    createtime: int,
    reply_id: str = DEFAULT_REPLY_VID,
    reply_name: str = DEFAULT_REPLY_NAME,
    template_id: str = DEFAULT_TEMPLATE_ID,
    form_id: str = DEFAULT_FORM_ID,
) -> WeComJournalEntry:
    return WeComJournalEntry(
        journalid=journalid,
        createtime=createtime,
        reply_id=reply_id,
        reply_name=reply_name,
        template_id=template_id,
        form_id=form_id,
        submission_type=1,
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
    `app/services/wecom_connection.py` and `app/services/wecom_sync.py`
    (structural typing — one stub satisfies both). Each of the three remote
    calls independently returns a fixed value or raises a fixed error;
    call counts are tracked so tests can assert a call was (or wasn't) made
    — e.g. `submit_daily` must never be invoked when a duplicate is merely
    "unprovable" (`docs/方案设计.md` §10.2).
    """

    def __init__(
        self,
        *,
        template_info: WeComTemplateInfo | None = None,
        template_error: WeComClientError | None = None,
        journal_page: WeComJournalPage | None = None,
        journal_error: WeComClientError | None = None,
        submission_result: WeComSubmissionResult | None = None,
        submit_error: WeComClientError | None = None,
    ) -> None:
        self.template_info = template_info if template_info is not None else build_template_info()
        self.template_error = template_error
        self.journal_page = (
            journal_page if journal_page is not None else WeComJournalPage(entries=[])
        )
        self.journal_error = journal_error
        self.submission_result = (
            submission_result if submission_result is not None else build_submission_result()
        )
        self.submit_error = submit_error
        self.closed = False
        self.get_template_info_calls = 0
        self.list_journals_calls = 0
        self.submit_daily_calls = 0

    async def get_template_info(
        self, cookie_jar: Sequence[WeComCookieIn], form_id: str
    ) -> WeComTemplateInfo:
        self.get_template_info_calls += 1
        if self.template_error is not None:
            raise self.template_error
        return self.template_info

    async def list_journals(
        self,
        cookie_jar: Sequence[WeComCookieIn],
        template_id: str,
        cursor: str | None,
        *,
        limit: int = 50,
    ) -> WeComJournalPage:
        self.list_journals_calls += 1
        if self.journal_error is not None:
            raise self.journal_error
        return self.journal_page

    async def submit_daily(
        self, cookie_jar: Sequence[WeComCookieIn], payload: WeComSubmitDailyPayload
    ) -> WeComSubmissionResult:
        self.submit_daily_calls += 1
        if self.submit_error is not None:
            raise self.submit_error
        return self.submission_result

    async def aclose(self) -> None:
        self.closed = True
