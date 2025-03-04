from urllib3 import Retry
import logging

logger = logging.getLogger(__name__)
logger.setLevel("INFO")

def log_retry(retry_state):
    logger.info(f"Retrying request  after {retry_state['backoff_time']} seconds.")


class LoggingRetry(Retry):
    def sleep(self, response=None):
        if response:
            retry_state = {
                "status_code": response.status,
                "backoff_time": self.get_backoff_time(),
            }
            log_retry(retry_state)
        super().sleep(response)
