"""The one HTTP call every adapter makes."""

import json
import urllib.error
import urllib.request

from .errors import PermanentError, TransientError


def post(url, payload, headers, timeout):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if 400 <= error.code < 500:
            raise PermanentError("%s: HTTP %d" % (url, error.code))
        raise TransientError("%s: HTTP %d" % (url, error.code))
    except (urllib.error.URLError, TimeoutError) as error:
        raise TransientError("%s: %s" % (url, error))
