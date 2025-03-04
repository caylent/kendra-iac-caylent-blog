from abc import ABC, abstractmethod
import time
import urllib3
import logging

from Retry.Retry import LoggingRetry

class CustomConnector(ABC):
    def __init__(self, data_source_id, index_id, kendra_job_execution_id, ssm_name, clients):
        self.data_source_id = data_source_id
        self.index_id = index_id
        self._kendra_job_execution_id = kendra_job_execution_id
        self.ssm_name = ssm_name
        self.url_session = None

        self.kendra_client = clients["kendra"]
        self.secrets_manager_client = clients["secrets_manager"]
        self.ssm_client = clients["parameter_store"]

        self.last_crawled_timestamp = self.retrieve_last_crawled_timestamp()
        self._is_sync_done = False

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel("INFO")

        self._build_url_session()

    def start_sync(self):
        if self._kendra_job_execution_id is not None:
            self.logger.info(f"Continuing syncing kendra_job_execution_id {self._kendra_job_execution_id}")
            return

        self.logger.info(f"Starting data source sync job for data source {self.data_source_id} and index {self.index_id}")
        retry = 0
        while True:
            try:
                result = self.kendra_client.start_data_source_sync_job(Id=self.data_source_id, IndexId=self.index_id)
                break
            except Exception as e:
                self.logger.info(f"Error starting data source sync job: {e}. Retrying...")
                if (retry > 5): raise(e)
                time.sleep(3^retry)
                retry += 1

        self.logger.info(result)
        self._kendra_job_execution_id = result["ExecutionId"]
        self.logger.info(f"Job execution ID: {self._kendra_job_execution_id}")

    def stop_sync(self):
        if self._kendra_job_execution_id:
            self.logger.info(f"Stopping data source sync job")
            result = self.kendra_client.stop_data_source_sync_job(Id=self.data_source_id, IndexId=self.index_id)
            self.logger.info(result)
        else:
            self.logger.info("No active data source sync job to stop")

    def batch_put_document(self, documents):
        if not documents:
            self.logger.info("No documents to put")
            return

        for i in range(0, len(documents), 10):
            batch = documents[i : i + 10]
            self.kendra_client.batch_put_document(IndexId=self.index_id, Documents=batch)

    def get_execution_id(self):
        return self._kendra_job_execution_id

    def get_is_sync_done(self):
        return self._is_sync_done

    def set_is_sync_done(self, is_sync_done):
        self._is_sync_done = is_sync_done

    def retrieve_last_crawled_timestamp(self):
        try:
            response = self.ssm_client.get_parameter(Name=self.ssm_name)
            return float(response["Parameter"]["Value"])
        except self.ssm_client.exceptions.ParameterNotFound:
            return 1.0
        except Exception as e:
            raise Exception(f"Error retrieving last crawled timestamp: {e} from {self.ssm_name}")
        
    def _build_url_session(self):
        retry_strategy = LoggingRetry(
            total=5,
            backoff_factor=1,
            status_forcelist=[400, 404, 429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        self.url_session = urllib3.PoolManager(retries=retry_strategy)

    @abstractmethod
    def get_documents(self, next_page=None):
        pass

    @abstractmethod
    def _get_secrets(self):
        pass
