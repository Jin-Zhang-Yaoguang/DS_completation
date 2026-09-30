from pathlib import Path
import tempfile
import unittest

from evaluate_bc_closed_loop import load_agent


class OpponentLoaderTest(unittest.TestCase):
    def test_supports_flat_sibling_imports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "helper.py").write_text("VALUE = 17\n", encoding="utf-8")
            main = root / "main.py"
            main.write_text(
                "from helper import VALUE\n\n"
                "def agent(obs, config):\n"
                "    return VALUE\n",
                encoding="utf-8",
            )

            agent = load_agent(main, "fixture_agent")

            self.assertEqual(agent(None, None), 17)

    def test_refreshes_sibling_modules_between_loads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            helper = root / "helper.py"
            helper.write_text("VALUE = 1\n", encoding="utf-8")
            main = root / "main.py"
            main.write_text(
                "from helper import VALUE\n\n"
                "def agent(obs, config):\n"
                "    return VALUE\n",
                encoding="utf-8",
            )
            self.assertEqual(load_agent(main, "fixture_agent_first")(None, None), 1)

            # A different source size invalidates timestamp-based bytecode
            # caches even on filesystems with coarse mtime resolution.
            helper.write_text("VALUE = 200\n", encoding="utf-8")

            self.assertEqual(load_agent(main, "fixture_agent_second")(None, None), 200)


if __name__ == "__main__":
    unittest.main()
