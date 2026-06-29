import unittest

from onshape_export_manager.core.retry import (
    DEFAULT_RETRY_HTTP_STATUSES,
    RetryPolicy,
    is_transient_exception,
    retry_decision,
    retry_statuses_from_config,
)


class RetryPolicyTests(unittest.TestCase):
    def test_backoff_is_exponential_and_capped(self) -> None:
        policy = RetryPolicy(backoff_base_seconds=2, backoff_max_seconds=5)

        self.assertEqual(policy.delay_seconds_for_attempt(0), 2)
        self.assertEqual(policy.delay_seconds_for_attempt(1), 4)
        self.assertEqual(policy.delay_seconds_for_attempt(2), 5)

    def test_retry_decision_for_status(self) -> None:
        policy = RetryPolicy(backoff_base_seconds=1)

        decision = retry_decision(
            attempt_index=0,
            max_attempts=3,
            policy=policy,
            status_code=503,
        )

        self.assertTrue(decision.should_retry)
        self.assertEqual(decision.delay_seconds, 1)

    def test_retry_decision_stops_at_max_attempts(self) -> None:
        policy = RetryPolicy()

        decision = retry_decision(
            attempt_index=2,
            max_attempts=3,
            policy=policy,
            status_code=503,
        )

        self.assertFalse(decision.should_retry)

    def test_transient_exception_classifier(self) -> None:
        class TimeoutErrorForTest(Exception):
            pass

        self.assertTrue(is_transient_exception(TimeoutErrorForTest()))
        self.assertFalse(is_transient_exception(ValueError()))

    def test_status_config_normalization(self) -> None:
        self.assertEqual(retry_statuses_from_config(None), DEFAULT_RETRY_HTTP_STATUSES)
        self.assertEqual(retry_statuses_from_config([429, 500]), (429, 500))


if __name__ == "__main__":
    unittest.main()
