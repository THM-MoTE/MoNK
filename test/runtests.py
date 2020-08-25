import unittest
import subprocess
import pathlib
import os
import io

# TODO implement smaller test cases


class TestSvg2Modelica(unittest.TestCase):
    def test_all_primitives(self):
        self.maxDiff = None
        res = subprocess.check_output([
            "python", "src/svg2modelica.py", "examples/all_primitives.svg"
        ])
        expected = ""
        fexp = "examples/all_primitives_expected.mo"
        with io.open(fexp, "r", encoding="utf-8") as f:
            expected = f.read()
        self.assertEqual(expected.strip(), res.decode("utf-8").strip())


if __name__ == "__main__":
    os.chdir(str(pathlib.Path(__file__).parents[1]))
    unittest.main()
