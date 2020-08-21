from csv import DictReader
import os

from mcmp_utils.api_client import SimpleApiClientBase
from mcmp_utils.tools.encryption import decrypt


ENCRYPTED_SLACK_TOKEN = 'gAAAAABeeL6GnpyMfUXt3t4dwZ_Ge5RH_4QTtYRSbhBt5WlD03J-tVsfaSUJAPcHH48ylbNj1loCFYC3UQdzcH0OVJ1TeheYPPUSb4UtDR28YiXuE-OIWnY8C3OYiMU3NyaXfXMAYPsVi0XXm6zxMfZpmLslsR7SHA=='


def common_slack_message_builder(environment_dict, results, expected_response_time):
    """
    Builds common slack message sections
    :param environment_dict: Dict of info about the environment
    :param results: The TestResults instance
    :param expected_response_time: The expected response time
    :return: Tuple of header, "slack attachments", summary
    """
    # Environment info
    header = "*API Validation Results*"
    for k, v in environment_dict.items():
        header += '\n' + f'{k.replace("_", " ").capitalize()}: {v}'

    attachments = []
    # Section: Failed & Skipped
    failed_text = ''
    skipped_text = ''
    for key in results.modules:
        for test_case_result in results.modules[key].tests:
            if test_case_result.status is False:
                failed_text += f'{results.modules[key].short_name}::{test_case_result.name}' + '\n'
            elif test_case_result.status is None:
                skipped_text += f'{results.modules[key].short_name}::{test_case_result.name}' + '\n'
    attachments.append(('#E33D0B', 'Failed Tests', failed_text))
    attachments.append(('#DCDCDC', 'Skipped Tests', skipped_text))

    # Section: API's exceeding expected response time
    metrics_dict = DictReader(open(os.path.join('logs', 'api_metrics.csv')))
    bad_timings = {}
    for row in metrics_dict:
        if row[metrics_dict.fieldnames[-1]] == 'False':
            key_name = f'{row[metrics_dict.fieldnames[0]]} {row[metrics_dict.fieldnames[1]]} {row[metrics_dict.fieldnames[2]]}'
            diff = float(row[metrics_dict.fieldnames[-2]])
            if key_name in bad_timings:
                bad_timings[key_name].append(diff)
            else:
                bad_timings[key_name] = [diff]

    bad_timing_with_average = ''
    for k, v in bad_timings.items():
        bad_timing_with_average += f'{k}\n\t- total: {len(v)} | average_time: {round(sum(v) / len(v), 4)}s\n'
    attachments.append(('#FF7F50', f"API's exceeding {expected_response_time} seconds", bad_timing_with_average))

    # Test run info
    summary = f'''
Total Tests: {results.total_tests}
Passed: {results.passed_tests}
Failed: {results.failed_tests}
Skipped: {results.skipped_tests}
Test Run Duration: {results.duration}'''
    return header, attachments, summary


def publish_results_to_slack(slack_channel: str, slack_app: str, secret: str, header: str, attachments: list, footer: str, zip_file=None):
    """
    Publishes Test Results to slack
    :param slack_channel: The channel to post to
    :param slack_app: The app to use
    :param secret: The key to decrypt the slack client token
    :param header: The first section of the report
    :param attachments: The middle section which are "slack attachments"
    :param footer: The last section of the report
    :param zip_file: The zipped file
    """
    payload = _build_results_for_slack(slack_channel, header, attachments, footer)
    status_code, response_body = getattr(SlackHookClient(), f'{slack_app}_post')(payload)
    print(status_code, response_body)
    if zip_file:
        upload_file_to_slack(zip_file, slack_channel, secret)


def upload_file_to_slack(file: str, slack_channel: str, secret: str):
    """
    uploads a zip file to slack
    :param file: The file path of the zipped file
    :param slack_channel: The slack channel to upload to
    :param secret: The key to decrypt the slack client token
    """
    os.system(f"curl -k -F file=@{file} -F channels={slack_channel} -F token={decrypt(ENCRYPTED_SLACK_TOKEN, secret)} https://slack.com/api/files.upload")


def publish_results_to_test_rail(results, username, password, suite_id):
    test_rail = TestRailClient(username, password, suite_id)
    for result in results:
        payload = _build_test_case_result_for_test_rail(result)
        test_rail.post(results.test_case_id, payload)


def _build_results_for_slack(slack_channel: str, header: str, attachments: list, footer: str) -> dict:
    """
    Builds the payload to use when posting Test Results to slack
    :param slack_channel: The channel to post to
    :param header: The first section of the report
    :param attachments: The middle section which are slack "attachments"
    :param footer: The last section of the report
    :return: slack Payload
    """
    body = {
        "channel": slack_channel,
        "username": "CBSCAMBot",
        "icon_emoji": ":mega:",
        "attachments": [
            {
                "pretext": header,
            }
        ]
    }
    body['attachments'] += [{
        "color": attachment[0],
        "title": attachment[1],
        "text": attachment[2]
    } for attachment in attachments]
    body['attachments'].append({"pretext": footer})
    return body


def _build_test_case_result_for_test_rail(result):
    if result.passed:
        status_id = 1
        comment = "Passed by E2E API Automation script"
    else:
        status_id = 5
        comment = result.error_message
    return {
        "status_id": status_id,
        "comment": comment,
        "elapsed": "5m",
        "version": "1.0 RC1"
    }


class SlackHookClient(SimpleApiClientBase):
    def __init__(self):
        super().__init__('https://hooks.slack.com/services/')

    def CBSCAMBot_post(self, payload):
        return self.post('T15GKHBT4/B3ZJ76VBP/q9gE4TOzdqgJya0Wpp9ZaC1h', payload)

    def icb_slack_post(self, payload):
        return self.post('T15GKHBT4/BCGP5B7D2/z6eLKPMqfK2FHNP4s1Dj8ONP', payload)

    def aiops_results_bot_post(self, payload):
        return self.post('T15GKHBT4/BFLJHHDJL/Sr85AnCPJ6GUBxLscDHDAeAC', payload)


class SlackClient(SimpleApiClientBase):
    def __init__(self):
        super().__init__('https://slack.com/')
        self._headers.update({'Content-Type': 'multipart/form-data'})

    def upload_zip(self, zip_file, channel, custom_file_name=None):
        # todo: figure out how to make it work; and decrypt slack token
        name = custom_file_name if custom_file_name else zip_file
        multipart_form_data = {
            'file': (name, open(zip_file, 'rb')),
            'channels': (None, channel),
            'token': (None, ENCRYPTED_SLACK_TOKEN)
        }
        return self.upload('api/files.upload', files=multipart_form_data)


class TestRailClient(SimpleApiClientBase):
    def __init__(self, user_name, password, run_id):
        super().__init__('https://gravitant.testrail.com/index.php')
        self.user_name = user_name
        self.password = password
        self.run_id = run_id

    def get_tests(self):
        return self.auth_get(f'?/api/v2/get_tests/{self.run_id}', self.user_name, self.password)

    def post_test(self, test_case_id, payload):
        return self.auth_post(f'?/api/v2/add_result_for_case/{self.run_id}/{test_case_id}', self.user_name, self.password, payload)
