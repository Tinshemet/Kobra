import unittest

from kobra import INSTANT, RECURRENCE, clock_in, clock_tail


class ClockTests(unittest.TestCase):
    def test_clock_tail_source_cases(self):
        cases = {
            "snapshot every vm at 21:30": "at 21:30",
            "stop every vm at 9pm": "at 9pm",
            "stop every vm at 9 pm": "at 9 pm",
            "restart the db vm at midnight": "at midnight",
            "check the lab at noon": "at noon",
            "stop the vms at the door": None,
            "launch every vm that is stopped": None,
            "put the vm at the lab network": None,
        }
        for request, expected in cases.items():
            with self.subTest(request=request):
                self.assertEqual(clock_tail(request), expected)

    def test_second_domain(self):
        self.assertEqual(clock_in("remind me every night"), RECURRENCE)
        self.assertEqual(clock_in("send the report tomorrow"), INSTANT)
        self.assertEqual(clock_tail("call Alex at 9 pm"), "at 9 pm")

    def test_quantification_is_not_recurrence(self):
        self.assertEqual(clock_in("archive every report"), "")
        self.assertEqual(clock_in("check every 2 hours"), RECURRENCE)

    def test_empty(self):
        self.assertEqual(clock_in(""), "")
        self.assertIsNone(clock_tail(""))

    def test_inherited_limit_is_visible(self):
        self.assertEqual(clock_tail("call at 29pm"), "at 29pm")


if __name__ == "__main__":
    unittest.main()
