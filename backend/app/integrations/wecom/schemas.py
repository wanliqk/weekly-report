"""Protocol DTOs for `WeComInternalClient` (`docs/方案设计.md` §2.4/§8).

These model the *raw* shape of the three verified WeCom internal endpoints —
not the local `wecom_sync_profiles`/`wecom_daily_sync_records` domain model
(`app/schemas/wecom.py`, `WECOM-02`, untouched by this task). Every remote
numeric/string identifier (`question_id`, `journalid`, `reply_id`, `vid`, ...)
is normalized to `str` at this boundary so callers never have to branch on
whether the remote happened to send an int or a string for the same field
(`docs/方案设计.md` §2.4: "协议中的数值型或字符串型标识统一在 Client 边界规范化为字符串").

`model_config = ConfigDict(extra="ignore")` on every inbound (remote-response)
model is deliberate: unknown extra fields are dropped rather than rejected,
so a harmless additive change on the remote side doesn't turn into a crash
here (`docs/方案设计.md` §8 point 4: "把未知额外字段忽略在协议 DTO 边界").
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _coerce_remote_id(value: object) -> object:
    """`int`/`str` remote identifiers both become `str`; anything else is
    left alone so Pydantic's normal type validation reports the real error."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return str(value)
    return value


RemoteId = Annotated[str, BeforeValidator(_coerce_remote_id)]


class WeComCookieIn(BaseModel):
    """One cookie jar entry.

    Wire shape matches Electron's `serializeCookieJar()` output exactly
    (`electron/src/main/wecom/bridge-client.ts`), which is also what
    `WECOM-06`'s Main-only endpoints will deserialize into this type before
    calling the Client (`docs/方案设计.md` §9.2/§2.3: "保存完整的结构化 Cookie
    jar,至少保留 name/value/domain/path/secure/httpOnly/sameSite/expirationDate").
    """

    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=256)
    value: str = Field(max_length=8192)
    domain: str = Field(min_length=1, max_length=256)
    path: str = Field(default="/", max_length=256)
    secure: bool
    http_only: bool
    same_site: Literal["unspecified", "no_restriction", "lax", "strict"]
    expiration_date: float | None = None


class WeComQuestionItem(BaseModel):
    """One `body.form.question.items[]` entry from `get_template_combine_info`."""

    model_config = ConfigDict(extra="ignore")

    question_id: RemoteId
    title: str
    reply_type: int
    must_reply: bool
    pos: int | None = None
    note: str | None = None
    ext: dict[str, Any] | None = None


class WeComTemplateEntry(BaseModel):
    """One `body.entrys[]` entry from `get_template_combine_info` — an
    existing submission summary, connect-time only (see
    `WeComFormDetailForkItem` for the execute-time equivalent used for
    duplicate-checking, sourced from a different endpoint/shape)."""

    model_config = ConfigDict(extra="ignore")

    journalid: RemoteId
    createtime: int
    reply_id: RemoteId
    reply_name: str
    form_id: RemoteId


class WeComTemplateInfo(BaseModel):
    """Return value of `WeComInternalClient.get_template_info()` (connect-time
    only — see `WeComFormDetail` for the execute-time equivalent)."""

    template_id: RemoteId
    form_id: RemoteId
    entries: list[WeComTemplateEntry]
    questions: list[WeComQuestionItem]


class WeComFormDetailForkItem(BaseModel):
    """One `body.stat_info.fork_items[]` entry from `formcol/detail` — one
    past submission of this recurring personal journal form. No per-user
    identity field exists on this entry (unlike the old, now-removed
    `get_journal_list` endpoint's `reply_id`); `formcol/detail` is only ever
    called with the current user's own Cookie against their own form, so
    every fork here is treated as this user's own submission history."""

    model_config = ConfigDict(extra="ignore")

    form_id: RemoteId
    ctime: int
    status: int


class WeComFormDetail(BaseModel):
    """Return value of `WeComInternalClient.get_form_detail()` — the
    execute-time structure/duplicate-check source (`GET /formcol/detail`),
    replacing the old `get_template_info()` re-check plus the separate,
    now-removed `list_journals()` duplicate-check call. `questions` reuses
    `WeComQuestionItem` (`formcol/detail`'s `question_infos[]` never carries
    `pos`/`note`/`ext`, all already-optional fields on that model)."""

    form_id: RemoteId
    creater_vid: RemoteId
    creater_name: str
    questions: list[WeComQuestionItem]
    fork_items: list[WeComFormDetailForkItem]


class WeComAnswerItem(BaseModel):
    """One already-mapped `question_id -> answer text` pair.

    Deciding *which* local field maps to which `question_id` is the Mapper's
    job (`WECOM-05`); this Client only knows how to serialize whatever items
    it's given into the exact `form_reply` shape `answer_page` expects.

    `rich_text` distinguishes the wire shape, not the content: a real
    captured submission (`docs/方案设计.md` §2.4) shows a WeCom "rich text"
    question (raw `reply_type` 24 — this integration's date/today/tomorrow
    trio's today/tomorrow questions, in the one live account observed so
    far) rejects/mangles a bare `text_reply` and instead needs
    `{"rich_text_reply": {"text_reply": "<div>...</div>", "plain_text_reply":
    "..."}}`; only the date question (`reply_type` 11) uses bare
    `text_reply`. Callers (`WeComSyncService`) set this from the freshly
    fetched question's raw remote `reply_type`, never from the locally
    stored `WeComReplyType` Literal (which collapses 1/24 to the same
    `"text"` bucket and was never meant to carry wire-format detail).
    """

    question_id: str = Field(min_length=1, max_length=64)
    text_reply: str = Field(max_length=10_000)
    rich_text: bool = False


class WeComSubmitDailyPayload(BaseModel):
    """Payload for `WeComInternalClient.submit_daily()`."""

    form_id: str = Field(min_length=1, max_length=128)
    template_id: str = Field(min_length=1, max_length=128)
    items: list[WeComAnswerItem] = Field(min_length=1)
    mngreporter_vids: list[str] = Field(default_factory=list)
    reporter_vids: list[str] = Field(default_factory=list)
    submit_again: bool = True


class WeComSubmissionResult(BaseModel):
    """Return value of `WeComInternalClient.submit_daily()`, distilled from
    `body.answer_replys[0]` and `body.user_vid`. `body.form` (current form
    structure) and the full `body.repeat_before_replys` contents are
    deliberately not modeled here — they're bulk/structural data for later
    stages (`WECOM-05`/`WECOM-06`) to fetch separately via `get_template_info`
    or reason about, not something this Client should retain."""

    answer_id: RemoteId
    reply_id: RemoteId
    journal_uuid: RemoteId
    user_vid: RemoteId
    has_repeat_before_replys: bool = False
