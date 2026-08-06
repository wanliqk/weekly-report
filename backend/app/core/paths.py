from app.core.config import Settings


def ensure_runtime_directories(settings: Settings) -> None:
    for directory in (
        settings.data_dir,
        settings.log_dir,
        settings.backup_dir,
        settings.export_temp_dir,
        settings.manual_backup_temp_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
