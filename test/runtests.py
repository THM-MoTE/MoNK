import unittest
import subprocess
import pathlib
import os

# TODO implement smaller test cases


class TestSvg2Modelica(unittest.TestCase):
    def test_all_primitives(self):
        self.maxDiff = None
        res = subprocess.run([
            "python", "src/svg2modelica.py", "examples/all_primitives.svg"
        ], capture_output=True)
        expected = ""
        fexp = "examples/all_primitives_expected.mo"
        with open(fexp, "r", encoding="utf-8") as f:
            expected = f.read()
        self.assertEqual(expected.strip(), res.stdout.decode("utf-8").strip())


if __name__ == "__main__":
    os.chdir(pathlib.Path(__file__).parents[1])
    unittest.main()