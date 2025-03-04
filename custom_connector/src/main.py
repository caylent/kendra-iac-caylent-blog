import json
import boto3
import logging
import os
import time

from CustomConnectors.JiraConnector import JiraConnector

LAST_CRAWLED_SSM_NAME = os.environ.get("LAST_CRAWLED_SSM_NAME")
CUSTOM_CONNECTOR_SELF_INVOKE_EVENT_SOURCE = os.environ.get("CUSTOM_CONNECTOR_SELF_INVOKE_EVENT_SOURCE")

logger = logging.getLogger(__name__)
logger.setLevel("INFO")

boto3_clients = {
    "kendra": boto3.client("kendra", "us-west-2"),
    "secrets_manager": boto3.client("secretsmanager"),
    "eventbridge": boto3.client("events"),
    "parameter_store": boto3.client("ssm"),
}

def handler(event):
    start_time = time.time()
    logger.info(f"Received Event: {event}")

    event_bridge_event_details = event.get("detail")

    index_id = event_bridge_event_details.get("index_id")
    data_source_name = event_bridge_event_details.get("data_source_name").lower()
    data_source_id = event_bridge_event_details.get("data_source_id")
    next_page_token = event_bridge_event_details.get("next_page_token", None)
    kendra_job_execution_id = event_bridge_event_details.get("kendra_job_execution_id", None)

    if data_source_name == "jira":
        custom_connector = JiraConnector(
            data_source_id=data_source_id,
            index_id=index_id,
            kendra_job_execution_id=kendra_job_execution_id,
            ssm_name=f"{LAST_CRAWLED_SSM_NAME}",
            clients=boto3_clients,
        )
    else:
        raise Exception(f"Invalid data source selected: {data_source_name}")

    custom_connector.start_sync()
    try:
        next_page = next_page_token
        while time.time() - start_time < 480:
            documents, next_page_token = custom_connector.get_documents(next_page)
            custom_connector.batch_put_document(documents)
            next_page = next_page_token

            if custom_connector.get_is_sync_done():
                boto3_clients["parameter_store"].put_parameter(
                    Name=custom_connector.ssm_name,
                    Value=str(time.time()),
                    Type="String",
                    Overwrite=True,
                )
                break
    except Exception as e:
        custom_connector.stop_sync()
        raise Exception(f"Error in lambda handler: {e}")

    if custom_connector.get_is_sync_done():
        custom_connector.stop_sync()
    else:
        try:
            response = boto3_clients["eventbridge"].put_events(
                Entries=[
                    {
                        "Source": CUSTOM_CONNECTOR_SELF_INVOKE_EVENT_SOURCE,
                        "DetailType": "SelfInvocation",
                        "Detail": json.dumps(
                            {
                                "index_id": index_id,
                                "data_source_name": data_source_name,
                                "data_source_id": data_source_id,
                                "next_page_token": next_page,
                                "kendra_job_execution_id": custom_connector.get_execution_id()
                            }
                        ),
                    }
                ]
            )
            logger.info(f"Lambda is continuing with next page token: {next_page} - EventBridge response: {response}")
            return {
                "statusCode": 200,
                "body": f"Lambda is continuing with response. Response from event_bridge: {response}",
                "headers": {"Content-Type": "application/json"},
            }
        except Exception as e:
            raise Exception(f"Error invoking lambda again: {e}")

    msg = f"{data_source_name} indexing complete."
    logger.info(msg)
    return {"statusCode": 200, "body": msg, "headers": {"Content-Type": "application/json"}}

def lambda_handler(event, context):
    try:
        return handler(event)
    except Exception as e:
        logger.error(f"Error in lambda handler: {e}")

        event_bridge_event_details = event.get("detail")
        index_id = event_bridge_event_details.get("index_id")
        data_source_id = event_bridge_event_details.get("data_source_id")
        boto3_clients["kendra"].stop_data_source_sync_job(Id=data_source_id, IndexId=index_id)
        
        return {"statusCode": 500, "body": str(e), "headers": {"Content-Type": "application/json"}}