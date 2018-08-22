#!/usr/bin/env python3

import os
import sys
import datetime
import pprint
import urllib
import requests
import json
import pprint

from google.cloud import storage
from google.oauth2 import service_account

raw_credentials = os.environ['GOOGLE_APPLICATION_CREDENTIALS_JSON']
account_info = json.loads(raw_credentials)
credentials = service_account.Credentials.from_service_account_info(account_info)
client = storage.Client(project=account_info['project_id'], credentials=credentials)

bucket = client.get_bucket('stanfordsnr-billing')
date = datetime.datetime.now().date() + datetime.timedelta(days=-1)
object_name = 'stanfordsnr-bill-%s.json' % date.isoformat()

blob = bucket.get_blob(object_name)

if not blob:
    sys.exit(1)

raw_bill = json.loads(blob.download_as_string())

bill = {} # project -> [billing data]
total = 0.0

for item in raw_bill:
    cost = float(item['cost']['amount'])
    credits = sum([float(x['amount']) for x in item.get('credits', []) if x is not None])
    total += cost

    bill[item['projectName']] = bill.get(item['projectName'], []) \
                              + [(":".join(item['lineItemId'].split("/")[2:]),
                                  cost, credits)]

message = "On **{date}**, you spent **${total:.2f}** on Google Cloud. Here's the breakdown:\n\n".format(
    date=date.strftime("%B %d, %Y"),
    total=total)

projects = sorted(bill.keys())

for project in projects:
    breakdown = bill[project]
    project_total = [0.0, 0.0]

    message += "**⬡ {project}**\n\n".format(project=project)
    message += "Service | Cost | Credits\n"
    message += "---|---|---\n"

    for s in breakdown:
        project_total[0] += s[1]
        project_total[1] += s[2]

        if s[1] == 0:
            continue

        message += "{title} | ${cost:.2f} | {sign}{credits:.2f}\n".format(title=s[0], cost=s[1], credits=abs(s[2]), sign='$' if s[2] >= 0 else '-$')

    message += "**Total** | **${cost:.2f}** | **{sign}{credits:.2f}**\n".format(cost=project_total[0], credits=abs(project_total[1]), sign='$' if project_total[1] >= 0 else '-$')

    message += "\n$$~$$\n"

message = message.strip()
print(message)

# data = [
#     ('type', 'stream'),
#     ('to', 'auto'),
#     ('subject', 'bills'),
#     ('content', message)
# ]
#
# response = requests.post(ZULIP_URL, data=data,
#                          auth=(ZULIP_BOT_EMAIL, ZULIP_BOT_TOKEN))
