import unittest
import subprocess

# TODO make this runnable from within sublime


class TestSvg2Modelica(unittest.TestCase):
    def test_all_primitives(self):
        res = subprocess.run([
            "python", "src/svg2modelica.py", "examples/all_primitives.svg"
        ], capture_output=True)
        expected = ""
        with open("examples/all_primitives.mo", "r", encoding="utf-8") as f:
            expected = f.read()
        self.assertEqual(expected, res.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
