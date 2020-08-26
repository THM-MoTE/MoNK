import unittest
import subprocess
import pathlib
import os
import io

# TODO implement smaller test cases


class TestSvg2Modelica(unittest.TestCase):
    def assertEqualStdout(self, expected, actual):
        def unify(s):
            s.strip().replace('\r\n', '\n')
        self.assertEqual(unify(expected), unify(actual))

    def test_all_primitives(self):
        self.maxDiff = None
        res = subprocess.check_output([
            "python", "src/svg2modelica.py", "--strict=true",
            "examples/all_primitives.svg"
        ])
        expected = ""
        fexp = "examples/all_primitives_expected.mo"
        with io.open(fexp, "r", encoding="utf-8") as f:
            expected = f.read()
        self.assertEqualStdout(expected, res.decode("utf-8"))


if __name__ == "__main__":
    os.chdir(str(pathlib.Path(__file__).parents[1]))
    unittest.main()
