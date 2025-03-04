import json
import os
from zoneinfo import ZoneInfo
from datetime import datetime, timezone
from CustomConnectors.CustomConnector import CustomConnector
import urllib3

JIRA_URL = os.environ.get("JIRA_URL") 
PROJECTS = os.environ.get("JIRA_PROJECTS")
JIRA_SECRET_NAME = os.environ.get("JIRA_SECRET_NAME")

class JiraConnector(CustomConnector):
    def __init__(self, data_source_id, index_id, kendra_job_execution_id, ssm_name, clients):
        super().__init__(data_source_id, index_id, kendra_job_execution_id, ssm_name, clients)
        self._email, self._api_token = self._get_secrets()
        self._auth_header = {
            **urllib3.util.make_headers(basic_auth=f'{self._email}:{self._api_token}'),
            'Accept': 'application/json',
            'Cache-Control': 'no-cache'
        }


        projects = [f'"{project}"' for project in PROJECTS.split(",")]
        self._jql = f"project IN ({','.join(projects)})"
        if self.last_crawled_timestamp:
            last_crawled_window = 120.0
            self._jql += f' AND updated > "{self._format_time(self.last_crawled_timestamp - last_crawled_window)}"'
        self._max_results = 100

    def get_documents(self, next_page=None):
        issues, next_page_token = self._crawl_data(next_page)
        documents = self._build_document(issues)
        return documents, next_page_token

    def _crawl_data(self, next_page):
        params = {
            "jql": self._jql,
            "maxResults": self._max_results,
            "fields": "id,description,summary,updated",  # Adjust fields as needed
        }
        if next_page:
            params["nextPageToken"] = next_page
        api_url = f"{JIRA_URL}/rest/api/3/search/jql"

        self.logger.info(f"Params: {params}")

        try:
            response = self.url_session.request(
                'GET',
                api_url,
                fields=params,
                headers=self._auth_header
            )
            if response.status >= 400:
                raise urllib3.exceptions.HTTPError(f"HTTP {response.status}: {response.data.decode('utf-8')}")
            
            data = json.loads(response.data.decode('utf-8'))
            issues = data.get("issues", [])
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                self.set_is_sync_done(True)

            return issues, next_page_token
        except Exception as e:
            self.logger.error(f"Error fetching issues: {e}")
            raise e

    def _build_document(self, issues):
        documents = []
        for issue in issues:
            issue_key = issue.get("key")
            project_key = issue.get("fields", {}).get("project", {}).get("key")
            issue_summary = issue.get("fields", {}).get("summary")
            issue_description = issue.get("fields", {}).get("description", {})
            issue_content = issue_description.get("content", []) if issue_description else []
            issue_blob = self._parse_adf(issue_content).strip()
            if issue_blob == '':  issue_blob = issue_summary

            issue_updated = issue.get("fields", {}).get("updated")

            doc = {
                "Id": f"ISSUE-{project_key}-{issue_key}",
                "Blob": issue_blob,
                "Title": issue_summary,
                "ContentType": "PLAIN_TEXT",
                "Attributes": [
                    {"Key": "_data_source_id", "Value": {"StringValue": self.data_source_id}},
                    {"Key": "_data_source_sync_job_execution_id", "Value": {"StringValue": self.get_execution_id()}},
                    {
                        "Key": "_source_uri",
                        "Value": {"StringValue": f"{JIRA_URL}/browse/{issue_key}"},
                    },
                    {
                        "Key": "_created_at",
                        "Value": {"DateValue": issue_updated},
                    },
                ],
            }
            documents.append(doc)
        return documents

    def _parse_adf(self, content):
        """
        Parse Atlassian Document Format (ADF) to plain text.
        Documentation on ADF can be found here: https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/
        """
        text_output = ""

        for node in content:
            node_type = node.get("type")

            if node_type == "text":
                text_output += self._parse_text(node)
            elif node_type == "hardBreak":
                text_output += " "
            elif node_type == "paragraph":
                text_output += self._parse_adf(node.get("content", []))
            elif node_type == "heading":
                level = node.get("attrs", {}).get("level", 1)
                text_output += f"{"#" * level}{self._parse_adf(node.get('content', []))}{"#" * level} "
            elif node_type == "inlineCard":
                url = node.get("attrs", {}).get("url", "")
                text_output += f"[{url}]"
            elif node_type in {"bulletList", "orderedList"}:
                text_output += "\n" + self._parse_list(node) + "\n"
            elif node_type == "blockquote":
                text_output += ">" + self._parse_adf(node.get("content", [])) + " "
            elif node_type == "codeBlock":
                language = node.get("attrs", {}).get("language", "")
                text_output += f"```{language} {self._parse_adf(node.get('content', []))}``` "
            elif node_type == "date":
                text_output += node.get("attrs", {}).get("timestamp", "")
            elif node_type == "emoji":
                text_output += node.get("attrs", {}).get("text", "")
            elif "content" in node:
                text_output += self._parse_adf(node["content"])
        return text_output

    def _parse_text(self, node):
        text = node.get("text", "")
        return text + " "

    def _parse_list(self, node):
        list_output = ""
        is_ordered = node["type"] == "orderedList"
        for index, item in enumerate(node.get("content", [])):
            if item["type"] == "listItem":
                prefix = f" {index + 1}. " if is_ordered else " - "
                list_output += prefix + self._parse_adf(item.get("content", [])) + "\n"
        return list_output

    def _get_secrets(self):
        secret = self.secrets_manager_client.get_secret_value(SecretId=JIRA_SECRET_NAME)
        secret_values = json.loads(secret.get("SecretString"))
        return secret_values.get("jiraId"), secret_values.get("jiraCredential")


    ''' Formats time 
    :param timestamp: timestamp in epoch format
    :return: formatted time as yyyy/MM/dd HH:mm in Jira server timezone
    '''
    def _format_time(self, timestamp: float):
        url = f"{JIRA_URL}/rest/api/3/myself"
        response = self.url_session.request(
            'GET',
            url,
            headers=self._auth_header
        )
        
        if response.status == 200:
            data = json.loads(response.data.decode('utf-8'))
            user_timezone = data.get("timeZone")
            user_tz = ZoneInfo(user_timezone)
            utc_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            user_local_time = utc_time.astimezone(user_tz)
            return user_local_time.strftime("%Y/%m/%d %H:%M")
        else:
            raise Exception("Failed to retrieve user timezone from Jira")
