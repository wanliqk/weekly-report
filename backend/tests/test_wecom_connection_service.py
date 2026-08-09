import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from conftest import STAGE5_PASSWORD
from sqlalchemy.ext.asyncio import AsyncEngine
from wecom_service_support import StubWeComClient, build_target_questions, build_template_info

from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.db.engine import create_engine
from app.db.migrate import run_startup_migrations
from app.db.session import create_session_factory
from app.integrations.wecom.client import WeComAuthExpired
from app.integrations.wecom.schemas import WeComQuestionItem
from app.models import User
from app.schemas.wecom import WeComFieldMappingConfig, WeComRecipientConfig
from app.services.bootstrap import BootstrapService
from app.services.wecom_connection import (
    WeComConnectionService,
    WeComNotConnectedError,
    WeComProfileVersionConflictError,
    WeComTemplateStructureUnresolvedError,
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
        assert recipient_config.reporter_vids == []
        field_mapping = WeComFieldMappingConfig.model_validate_json(profile.field_mapping_json)
        assert field_mapping.rules == []
        assert field_mapping.unmapped_policy == "block"

    # An injected client is caller-owned; the Service only auto-closes a
    # client it constructed itself (`_new_client()`'s `owns_client` guard).
    assert stub.closed is False


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
) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    # Only a "today" question survives — "date" and "tomorrow" hints never match.
    incomplete_questions = [
        WeComQuestionItem(question_id="1", title="今日工作", reply_type=1, must_reply=True, pos=1)
    ]
    stub = StubWeComClient(template_info=build_template_info(questions=incomplete_questions))

    async with session_factory() as session:
        with pytest.raises(WeComTemplateStructureUnresolvedError):
            await WeComConnectionService(session, client=stub).validate_connection(
                user.id, cookie_jar=[], credential_slot="slot-1", form_id="form-1"
            )

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
                recipient_config=None,
                field_mapping=None,
            )


async def test_update_profile_only_touches_recipient_and_field_mapping(
    wecom_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(wecom_engine)
    user = await _bootstrap_user(session_factory)
    async with session_factory() as session:
        await WeComConnectionService(session, client=StubWeComClient()).validate_connection(
            user.id, cookie_jar=[], credential_slot="slot-1", form_id="form-1"
        )

    new_recipient_config = WeComRecipientConfig(
        schema_version=1, mngreporter_vids=["9000000000000099"], reporter_vids=[], remote_version=1
    )
    async with session_factory() as session:
        updated = await WeComConnectionService(session).update_profile(
            user.id,
            expected_version=1,
            recipient_config=new_recipient_config,
            field_mapping=None,
        )

    assert updated.version == 2
    recipient_config = WeComRecipientConfig.model_validate_json(updated.recipient_config_json)
    assert recipient_config.mngreporter_vids == ["9000000000000099"]
    # question_mapping / schema_fingerprint / form_id are connect-time-only
    # (`WeComProfileUpdateRequest`'s docstring) and must be untouched.
    assert updated.form_id == "SYNTHETIC-FORM-0000000000000000000fork"


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
