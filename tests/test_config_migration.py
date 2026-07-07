import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cairos.config import ConfigError, backup_config, config_path, load_config, migrate_config_file, save_config


class ConfigMigrationTests(unittest.TestCase):
    def with_home(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return temp.name

    def write_config(self, home: str, data: object) -> Path:
        path = Path(home) / ".config" / "cairos" / "config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_old_flat_ai_config_migrates_with_backup(self):
        home = self.with_home()
        self.write_config(home, {"ai": {"provider": "openai", "model": "old"}, "unknown": {"keep": True}})
        with patch.dict(os.environ, {"HOME": home}, clear=False):
            cfg = load_config()
            self.assertEqual(cfg["schema_version"], 1)
            self.assertEqual(cfg["ai"]["model"], "old")
            self.assertEqual(cfg["unknown"]["keep"], True)
            self.assertTrue(list(config_path().parent.glob("config.backup-*.json")))

    def test_profiles_and_active_profile_preserved(self):
        home = self.with_home()
        self.write_config(
            home,
            {
                "schema_version": 1,
                "ai_profiles": {"openrouter-free": {"provider": "openai", "model": "openrouter/free"}},
                "active_ai_profile": "openrouter-free",
            },
        )
        with patch.dict(os.environ, {"HOME": home}, clear=False):
            cfg = load_config()
            self.assertIn("openrouter-free", cfg["ai_profiles"])
            self.assertEqual(cfg["active_ai_profile"], "openrouter-free")

    def test_backup_command_returns_copy(self):
        home = self.with_home()
        self.write_config(home, {"schema_version": 1})
        with patch.dict(os.environ, {"HOME": home}, clear=False):
            backup = backup_config()
            self.assertIsNotNone(backup)
            assert backup is not None
            self.assertTrue(backup.exists())

    def test_migrate_config_file_no_backup_when_current(self):
        home = self.with_home()
        with patch.dict(os.environ, {"HOME": home}, clear=False):
            save_config(load_config())
            migrate_config_file()
            before = list(config_path().parent.glob("config.backup-*.json"))
            migrate_config_file()
            after = list(config_path().parent.glob("config.backup-*.json"))
            self.assertEqual(before, after)

    def test_corrupted_json_is_not_overwritten(self):
        home = self.with_home()
        path = Path(home) / ".config" / "cairos" / "config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{broken", encoding="utf-8")
        with patch.dict(os.environ, {"HOME": home}, clear=False):
            with self.assertRaises(ConfigError):
                load_config()
            self.assertEqual(path.read_text(encoding="utf-8"), "{broken")


if __name__ == "__main__":
    unittest.main()
