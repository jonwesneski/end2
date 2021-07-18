from datetime import datetime
import json
import logging
import os


class HarFileHandler(logging.FileHandler):
    def __init__(self, filename, mode: str, encoding: str=None, delay: bool=False, errors=None,
        version="1.2", creator_version="537.36", pages_title="HAR Generator") -> None:
        super().__init__(filename, mode=mode, encoding=encoding, delay=delay)
        self._starter(version, creator_version, pages_title)

    def _starter(self, version, creator_version, pages_title):
        starter = f'''{{
  "log": {{
    "version": "{version}",
    "creator": {{
      "name": "WebInspector",
      "version": "{creator_version}"
    }},
    "pages": [
      {{
        "startedDateTime": "{datetime.now().strftime("%Y-%m-%dT%H:%M:%S.123Z")}",
        "id": "page_1",
        "title": "{pages_title}",
        "pageTimings": {{
          "onContentLoad": 908.7060000747442,
          "onLoad": 2029.8569998703897
        }}
      }}
    ],
    "entries": [
'''
        self.emit(logging.makeLogRecord({'msg': starter}))

    def _closer(self):
        closer = '''    ]
  }
}
'''
        self.emit(logging.makeLogRecord({'msg': closer}))

    def close(self) -> None:
        self._closer()
        return super().close()


class HarLogger:
    def __init__(self):
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        file_handler = HarFileHandler(os.path.join('logs', 'test.har'), mode='w')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(fmt=f'%(message)s'))
        self.logger.addHandler(file_handler)
        self.entry_delimiter = ""

    def info(self, request, response):
        entry = self._make_entry(request, response)
        self.logger.info(entry)

    def debug(self, response):
        pass

    def warning(self, response):
        pass

    def critical(self, response):
        pass

    def error(self, response):
        pass

    def _make_entry(self, request, response):
        entry = self.entry_delimiter + f'''{{
        "_fromCache": "disk",
        "_initiator": {{
          "type": "script",
          "stack": {{}}
        }},
        "_priority": "High",
        "_resourceType": "fetch",
        "cache": {{}},
        "pageref": "page_1",
        "request": {{
          "method": "{response._method}",
          "url": "https://github.com/python/cpython/security/overall-count",
          "httpVersion": "http/2.0",
          "headers": [],
          "queryString": [],
          "cookies": [],
          "headersSize": -1,
          "bodySize": 0
        }},
        "response": {{
          "status": {response.status},
          "statusText": "{response.reason}",
          "httpVersion": "http/2.0",
          "headers": {self._make_headers(response.headers._headers)},
          "cookies": [],
          "content": {{
            "size": 0,
            "mimeType": "{response.headers._default_type}",
            "text": ""
          }},
          "redirectURL": "",
          "headersSize": -1,
          "bodySize": 0,
          "_transferSize": 0,
          "_error": null
        }},
        "serverIPAddress": "140.82.113.4",
        "startedDateTime": "2021-07-09T01:35:50.068Z",
        "time": 4.252000013366342,
        "timings": {{
          "blocked": 1.195999818906188,
          "dns": -1,
          "ssl": -1,
          "connect": -1,
          "send": 0,
          "wait": 1.8329999623298645,
          "receive": 1.223000232130289,
          "_blocked_queueing": 1.076999818906188
        }}
      }}'''
        self.entry_delimiter = ",\n"
        return entry

    def _make_headers(self, r_headers, indent=2*6):
      list_dict = [{"name": header[0], "values": header[1]} for header in r_headers]
      return json.dumps(list_dict, indent=indent)


# a = HarLogger()
# from urllib import request
# with request.urlopen('https://google.com', timeout=3) as response:
#     print(response)
#     a.info(None, response)
#     b =1