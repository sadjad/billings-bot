#!/usr/bin/env python3

import os
import datetime
import pprint
import urllib
import boto3
import requests

# following environment variables are needed:
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - ZULIP_BOT_EMAIL
# - ZULIP_BOT_TOKEN
# - ZULIP_URL
#
# The AWS user needs permissions for Cost Explorer

ZULIP_URL = urllib.parse.urljoin(os.environ["ZULIP_URL"], "api/v1/messages")
ZULIP_BOT_EMAIL = os.environ["ZULIP_BOT_EMAIL"]
ZULIP_BOT_TOKEN = os.environ["ZULIP_BOT_TOKEN"]

end_date = datetime.datetime.now().date()
start_date = end_date + datetime.timedelta(days=-1)

BREAKDOWN_COUNT = 10

def normalize(name):
    return name.replace("Amazon Elastic Compute Cloud", "Amazon EC2") \
               .replace("Amazon Simple Storage Service", "Amazon S3" ) \
               .replace("Amazon Relational Database Service", "Amazon RDS")

client = boto3.client('ce')
cost_and_usage = client.get_cost_and_usage(
    TimePeriod={
        'Start': start_date.isoformat(),
        'End': end_date.isoformat()
    },
    Granularity='DAILY',
    Metrics=['UnblendedCost'],
    GroupBy=[{
        "Type": "DIMENSION",
        "Key": "SERVICE"
    }],
    #Filter={"Not": {"Dimensions": {"Key": "RECORD_TYPE","Values": ["Credit", "Refund", "Upfront"]}}}
)

spendings = [(float(x['Metrics']['UnblendedCost']['Amount']), normalize(x['Keys'][0]))
             for x in cost_and_usage['ResultsByTime'][0]['Groups']]
total = sum([x[0] for x in spendings])

spendings.sort(key=lambda x: x[0], reverse=True)

message = """On **{date}**, you spent **${total:.2f}** on AWS. Here's the breakdown:\n\n""".format(
    date=start_date.strftime("%B %d, %Y"),
    total=total)

message += "Service | Amount\n"
message += "---|---\n"

for s in spendings[:BREAKDOWN_COUNT]:
    message += "{title} | ${amount:.2f}\n".format(title=s[1], amount=s[0])

if len(spendings) > BREAKDOWN_COUNT:
    message += "Other | ${amount:.2f}\n".format(amount=sum([x[0] for x in spendings[BREAKDOWN_COUNT:]]))

message += "**Total** | **${amount:.2f}**".format(amount=total)

data = [
    ('type', 'stream'),
    ('to', 'auto'),
    ('subject', 'aws-costs'),
    ('content', message)
]

response = requests.post(ZULIP_URL, data=data,
                         auth=(ZULIP_BOT_EMAIL, ZULIP_BOT_TOKEN))
