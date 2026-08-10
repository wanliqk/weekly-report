import asyncio
import logging
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from conftest import STAGE5_PASSWORD
from sqlalchemy.ext.asyncio import AsyncEngine
from wecom_service_support import (
    DEFAULT_FORM_ID,
    DEFAULT_REPLY_NAME,
    DEFAULT_REPLY_VID,
    StubWeComClient,
    build_target_questions,
    build_template_info,
)

from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.core.ulid import generate_ulid
from app.db.engine import create_engine
from app.db.migrate import run_startup_migrations
from app.db.session import create_session_factory
from app.integrations.wecom.client import WeComAuthExpired
from app.integrations.wecom.schemas import WeComQuestionItem, WeComTemplateEntry
from app.models import User
from app.schemas.wecom import WeComFieldMappingConfig, WeComFieldMappingRule, WeComRecipientConfig
from app.services.bootstrap import BootstrapService
from app.services.wecom_connection import (
    WeComConnectionService,
    WeComNotConnectedError,
    WeComProfileVersionConflictError,
    WeComTemplateStructureUnresolvedError,
    build_question_spec,
)


@pytest.fixture
def wecom_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        environment="test", data_dir=tmp_path / "data", backup_dir=tmp_path / "backups"
    )
    ensure_runtime_directories(settings)
    run_startup_migrations(settings)
    return settings


@pytest.fixture
async def wecom_engine(wecom_settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(wecom_settings)
    try:
        yield engine
    finally:
        await engine.dispose()


async def _bootstrap_user(session_factory: object, *, username: str = "owner") -> User:
    async with session_factory() as session:  # type: ignore[operator]
        return await BootstrapService(session).bootstrap(
            username=username, password=STAGE5_PASSWORD, display_name="Owner"
        )


def test_build_question_spec_supports_live_text_reply_type() -> None:
    item = WeComQuestionItem(
        question_id="SYNTHETIC-LIVE-TEXT-QUESTION",
        title="今日工作",
        reply_type=24,
        must_reply=True,
        pos=2,
    )

    spec = build_question_spec(item, submit_order=2)

    assert spec is not None
    assert spec.question_id == "SYNTHETIC-LIVE-TEXT-QUESTION"
    assert spec.reply_type == "text"
    assert spec.submit_order == 2


async def test_validate_connection_creates_binding_and_active_profile(
    wecom_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    stub = StubWeComClient()

    async with session_factory() as session:
        await WeComConnectionService(session, client=stub).validate_connection(
            user.id, cookie_jar=[], credential_slot="slot-1", form_id="form-1"
        )

    async with session_factory() as session:
        binding = await WeComConnectionService(session).get_binding(user.id)
        assert binding is not None
        assert binding.status == "connected"
        assert binding.credential_slot == "slot-1"
        assert binding.wecom_vid == "9000000000000011"
        assert binding.version == 1

        profile = await WeComConnectionService(session).get_profile(user.id)
        assert profile.is_active is True
        assert profile.version == 1
        assert profile.form_id == "SYNTHETIC-FORM-0000000000000000000fork"
        recipient_config = WeComRecipientConfig.model_validate_json(profile.recipient_config_json)
        assert recipient_config.mngreporter_vids == []
        # `ISS-042`: defaults to the connecting user's own best-guess vid
        # (proven by real submitted traffic to be required — WeCom rejects a
        # write with no reporter at all), not an empty list.
        assert recipient_config.reporter_vids == [binding.wecom_vid]
        field_mapping = WeComFieldMappingConfig.model_validate_json(profile.field_mapping_json)
        assert field_mapping.rules == []
        assert field_mapping.unmapped_policy == "block"

    # An injected client is caller-owned; the Service only auto-closes a
    # client it constructed itself (`_new_client()`'s `owns_client` guard).
    assert stub.closed is False


async def test_validate_connection_leaves_reporter_vids_empty_without_a_best_guess_entry(
    wecom_engine: AsyncEngine,
) -> None:
    """`ISS-042`: defaulting `reporter_vids` to the best-guess `wecom_vid`
    must not turn into `[""]` (which `WeComRecipientConfig`'s
    `_vids_are_non_blank` validator rejects, crashing the whole connect
    flow) when there is no best-guess entry to guess from at all."""
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    stub = StubWeComClient(template_info=build_template_info(entries=[]))

    async with session_factory() as session:
        await WeComConnectionService(session, client=stub).validate_connection(
            user.id, cookie_jar=[], credential_slot="slot-1", form_id="form-1"
        )

    async with session_factory() as session:
        binding = await WeComConnectionService(session).get_binding(user.id)
        assert binding is not None
        assert binding.wecom_vid == ""

        profile = await WeComConnectionService(session).get_profile(user.id)
        recipient_config = WeComRecipientConfig.model_validate_json(profile.recipient_config_json)
        assert recipient_config.reporter_vids == []


async def test_validate_connection_prefers_reportvids_over_the_connecting_users_own_vid(
    wecom_engine: AsyncEngine,
) -> None:
    """`ISS-052`: real captures show `entrys[0].reportvids` is WeCom's own
    already-resolved recipient list (the template's configured approvers) —
    never the submitting user's own vid. It must win over `ISS-042`'s
    self-vid fallback whenever a real entry provides it, since real traffic
    later proved the self-targeted default itself gets rejected too."""
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    entry = WeComTemplateEntry(
        journalid="SYNTHETIC-JOURNAL-0000000000000002",
        createtime=1700000000,
        reply_id=DEFAULT_REPLY_VID,
        reply_name=DEFAULT_REPLY_NAME,
        form_id=DEFAULT_FORM_ID,
        reportvids=["9000000000000099", "9000000000000098"],
    )
    stub = StubWeComClient(template_info=build_template_info(entries=[entry]))

    async with session_factory() as session:
        await WeComConnectionService(session, client=stub).validate_connection(
            user.id, cookie_jar=[], credential_slot="slot-1", form_id="form-1"
        )

    async with session_factory() as session:
        profile = await WeComConnectionService(session).get_profile(user.id)
        recipient_config = WeComRecipientConfig.model_validate_json(profile.recipient_config_json)
        assert recipient_config.reporter_vids == ["9000000000000099", "9000000000000098"]
        assert recipient_config.mngreporter_vids == []


async def test_validate_connection_falls_back_to_own_vid_when_entry_has_no_reportvids(
    wecom_engine: AsyncEngine,
) -> None:
    """A legacy/older capture shape or an entry that simply never carried
    `reportvids` must fall back to `ISS-042`'s self-vid default, exactly as
    before this change — `reportvids` is preferred, not required."""
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    stub = StubWeComClient(template_info=build_template_info())

    async with session_factory() as session:
        await WeComConnectionService(session, client=stub).validate_connection(
            user.id, cookie_jar=[], credential_slot="slot-1", form_id="form-1"
        )

    async with session_factory() as session:
        binding = await WeComConnectionService(session).get_binding(user.id)
        assert binding is not None
        profile = await WeComConnectionService(session).get_profile(user.id)
        recipient_config = WeComRecipientConfig.model_validate_json(profile.recipient_config_json)
        assert recipient_config.reporter_vids == [binding.wecom_vid]


async def test_validate_connection_maps_auth_error_and_persists_nothing(
    wecom_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    stub = StubWeComClient(template_error=WeComAuthExpired("login expired"))

    async with session_factory() as session:
        with pytest.raises(WeComNotConnectedError):
            await WeComConnectionService(session, client=stub).validate_connection(
                user.id, cookie_jar=[], credential_slot="slot-1", form_id="form-1"
            )

    async with session_factory() as session:
        assert await WeComConnectionService(session).get_binding(user.id) is None


async def test_validate_connection_rejects_incomplete_template_and_persists_nothing(
    wecom_engine: AsyncEngine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    # Only a "today" question survives — "date" and "tomorrow" hints never match.
    incomplete_questions = [
        WeComQuestionItem(question_id="1", title="今日工作", reply_type=1, must_reply=True, pos=1)
    ]
    stub = StubWeComClient(template_info=build_template_info(questions=incomplete_questions))

    target_logger = logging.getLogger("app.integrations.wecom.connection")
    was_disabled = target_logger.disabled
    target_logger.disabled = False
    try:
        async with session_factory() as session:
            with (
                caplog.at_level(logging.DEBUG, logger=target_logger.name),
                pytest.raises(WeComTemplateStructureUnresolvedError),
            ):
                await WeComConnectionService(session, client=stub).validate_connection(
                    user.id, cookie_jar=[], credential_slot="slot-1", form_id="form-1"
                )
    finally:
        target_logger.disabled = was_disabled

    diagnostic_records = [
        record for record in caplog.records if "outcome=template_unresolved" in record.getMessage()
    ]
    assert diagnostic_records
    diagnostics = diagnostic_records[-1].__dict__["wecom_diagnostics"]
    assert diagnostics["question_count"] == 1
    assert diagnostics["recognized_question_count"] == 1
    assert diagnostics["date_candidate_count"] == 0
    assert diagnostics["today_candidate_count"] == 1
    assert diagnostics["tomorrow_candidate_count"] == 0
    assert diagnostics["date_reply_type"] is None
    assert diagnostics["today_reply_type"] == 1
    assert diagnostics["tomorrow_reply_type"] is None

    async with session_factory() as session:
        assert await WeComConnectionService(session).get_binding(user.id) is None


async def test_reconnect_updates_existing_binding_and_profile_in_place(
    wecom_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    async with session_factory() as session:
        await WeComConnectionService(session, client=StubWeComClient()).validate_connection(
            user.id, cookie_jar=[], credential_slot="slot-1", form_id="form-1"
        )

    reconnect_questions = build_target_questions()
    stub = StubWeComClient(
        template_info=build_template_info(form_id="another-form", questions=reconnect_questions)
    )
    async with session_factory() as session:
        await WeComConnectionService(session, client=stub).validate_connection(
            user.id, cookie_jar=[], credential_slot="slot-2", form_id="another-form"
        )

    async with session_factory() as session:
        binding = await WeComConnectionService(session).get_binding(user.id)
        assert binding is not None
        assert binding.credential_slot == "slot-2"
        assert binding.version == 2
        profile = await WeComConnectionService(session).get_profile(user.id)
        assert profile.form_id == "another-form"
        assert profile.version == 2


async def test_reconnect_preserves_field_mapping_but_refreshes_recipient_config(
    wecom_engine: AsyncEngine,
) -> None:
    """Reconnecting (e.g. to a different `form_id`) must not silently wipe a
    user's already-working `field_mapping` back to the first-connect
    default, even though the *remote* form's date/today/tomorrow question
    structure is re-discovered fresh every time — `field_mapping` is keyed
    by this app's own template `field_key` and has no relationship to which
    WeCom form is connected (`PROD-030`). `recipient_config` is the
    opposite: it is never user-edited (`PROD-032`), so a reconnect *should*
    refresh it to whatever the template currently resolves to, rather than
    keep whatever was resolved at the previous connect."""
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    async with session_factory() as session:
        await WeComConnectionService(session, client=StubWeComClient()).validate_connection(
            user.id, cookie_jar=[], credential_slot="slot-1", form_id="form-1"
        )

    custom_field_key = generate_ulid()
    custom_field_mapping = WeComFieldMappingConfig(
        schema_version=1,
        rules=[WeComFieldMappingRule(field_key=custom_field_key, target="today_work")],
        unmapped_policy="ignore",
    )
    async with session_factory() as session:
        await WeComConnectionService(session).update_profile(
            user.id,
            expected_version=1,
            field_mapping=custom_field_mapping,
        )

    reconnect_questions = build_target_questions()
    reconnect_entry = WeComTemplateEntry(
        journalid="SYNTHETIC-JOURNAL-RECONNECT-0000001",
        createtime=1700000000,
        reply_id=DEFAULT_REPLY_VID,
        reply_name=DEFAULT_REPLY_NAME,
        form_id="another-form",
        reportvids=["9000000000000077"],
    )
    stub = StubWeComClient(
        template_info=build_template_info(
            form_id="another-form", questions=reconnect_questions, entries=[reconnect_entry]
        )
    )
    async with session_factory() as session:
        await WeComConnectionService(session, client=stub).validate_connection(
            user.id, cookie_jar=[], credential_slot="slot-2", form_id="another-form"
        )

    async with session_factory() as session:
        profile = await WeComConnectionService(session).get_profile(user.id)
        assert profile.form_id == "another-form"
        assert profile.version == 3
        field_mapping = WeComFieldMappingConfig.model_validate_json(profile.field_mapping_json)
        assert field_mapping == custom_field_mapping
        recipient_config = WeComRecipientConfig.model_validate_json(profile.recipient_config_json)
        assert recipient_config.reporter_vids == ["9000000000000077"]


async def test_concurrent_validate_connection_only_creates_one_binding_and_profile(
    wecom_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)

    async def _attempt(slot: str) -> None:
        async with session_factory() as session:
            await WeComConnectionService(session, client=StubWeComClient()).validate_connection(
                user.id, cookie_jar=[], credential_slot=slot, form_id="form-1"
            )

    # Same `credential_slot` on both attempts is deliberate: it forces
    # whichever insert loses the race to hit the IntegrityError fallback
    # path (on the `uq_wecom_user_bindings_credential_slot` constraint, not
    # just `uq_wecom_user_bindings_user_id`) deterministically rather than
    # relying on asyncio scheduling luck.
    await asyncio.gather(_attempt("race-slot"), _attempt("race-slot"))

    async with session_factory() as session:
        binding = await WeComConnectionService(session).get_binding(user.id)
        assert binding is not None
        profile = await WeComConnectionService(session).get_profile(user.id)
        assert profile is not None


async def test_get_profile_requires_a_connection_first(wecom_engine: AsyncEngine) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)

    async with session_factory() as session:
        with pytest.raises(WeComNotConnectedError):
            await WeComConnectionService(session).get_profile(user.id)


async def test_update_profile_rejects_stale_version(wecom_engine: AsyncEngine) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    async with session_factory() as session:
        await WeComConnectionService(session, client=StubWeComClient()).validate_connection(
            user.id, cookie_jar=[], credential_slot="slot-1", form_id="form-1"
        )

    async with session_factory() as session:
        with pytest.raises(WeComProfileVersionConflictError):
            await WeComConnectionService(session).update_profile(
                user.id,
                expected_version=99,
                field_mapping=WeComFieldMappingConfig(schema_version=1, rules=[]),
            )


async def test_update_profile_only_touches_field_mapping(
    wecom_engine: AsyncEngine,
) -> None:
    """`recipient_config` is never user-editable (`PROD-032`) — `update_profile()`
    only ever writes `field_mapping_json`; connect-time-only columns
    (`question_mapping`/`schema_fingerprint`/`form_id`/`recipient_config`)
    must stay exactly what `validate_connection()` produced."""
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    async with session_factory() as session:
        await WeComConnectionService(session, client=StubWeComClient()).validate_connection(
            user.id, cookie_jar=[], credential_slot="slot-1", form_id="form-1"
        )
        original_profile = await WeComConnectionService(session).get_profile(user.id)

    custom_field_key = generate_ulid()
    new_field_mapping = WeComFieldMappingConfig(
        schema_version=1,
        rules=[WeComFieldMappingRule(field_key=custom_field_key, target="today_work")],
        unmapped_policy="ignore",
    )
    async with session_factory() as session:
        updated = await WeComConnectionService(session).update_profile(
            user.id,
            expected_version=1,
            field_mapping=new_field_mapping,
        )

    assert updated.version == 2
    field_mapping = WeComFieldMappingConfig.model_validate_json(updated.field_mapping_json)
    assert field_mapping == new_field_mapping
    # question_mapping / schema_fingerprint / form_id / recipient_config are
    # connect-time-only (`WeComProfileUpdateRequest`'s docstring) and must be
    # untouched.
    assert updated.form_id == "SYNTHETIC-FORM-0000000000000000000fork"
    assert updated.recipient_config_json == original_profile.recipient_config_json


async def test_disconnect_marks_status_and_is_a_noop_without_a_binding(
    wecom_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)

    async with session_factory() as session:
        # No binding exists yet; must not raise.
        await WeComConnectionService(session).disconnect(user.id)

    async with session_factory() as session:
        await WeComConnectionService(session, client=StubWeComClient()).validate_connection(
            user.id, cookie_jar=[], credential_slot="slot-1", form_id="form-1"
        )
    async with session_factory() as session:
        await WeComConnectionService(session).disconnect(user.id)

    async with session_factory() as session:
        binding = await WeComConnectionService(session).get_binding(user.id)
        assert binding is not None
        assert binding.status == "disconnected"
        assert binding.version == 2
