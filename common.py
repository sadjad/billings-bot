import os
import urllib.parse

ZULIP_URL = urllib.parse.urljoin(os.environ["ZULIP_URL"], "api/v1/messages")
ZULIP_BOT_EMAIL = os.environ["ZULIP_BOT_EMAIL"]
ZULIP_BOT_TOKEN = os.environ["ZULIP_BOT_TOKEN"]
