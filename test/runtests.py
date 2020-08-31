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

    def setUp(self):
        self.maxDiff = None  # allow large string diffs

    def get_expected_and_actual(self, fname):
        res = subprocess.check_output([
            "python", "src/svg2modelica.py", "--strict=true",
            str(pathlib.Path("examples") / (fname + ".svg"))
        ])
        expected = ""
        fexp = pathlib.Path("examples") / (fname + "_expected.mo")
        with io.open(str(fexp), "r", encoding="utf-8") as f:
            expected = f.read()
        return res.decode("utf-8"), expected

    def test_all_primitives(self):
        act, exp = self.get_expected_and_actual("all_primitives")
        self.assertEqualStdout(exp, act)

    def test_group_transform(self):
        act, exp = self.get_expected_and_actual("group_transform")
        self.assertEqualStdout(exp, act)


if __name__ == "__main__":
    os.chdir(str(pathlib.Path(__file__).parents[1]))
    unittest.main()
