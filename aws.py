#!/usr/bin/env python3

import os
import datetime
import pprint
import urllib
import boto3
import requests

from common import *

# following environment variables are needed:
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - ZULIP_BOT_EMAIL
# - ZULIP_BOT_TOKEN
# - ZULIP_URL
#
# The AWS user needs permissions for Cost Explorer

end_date = datetime.datetime.now().date()
start_date = end_date + datetime.timedelta(days=-1)

BREAKDOWN_COUNT = 10

def normalize(name):
    return name.replace("Amazon Elastic Compute Cloud", "Amazon EC2") \
               .replace("Amazon Simple Storage Service", "Amazon S3" ) \
               .replace("Amazon Relational Database Service", "Amazon RDS") \
               .replace("Amazon Elastic Container Service for Kubernetes", "Amazon ECS") \
               .replace("Amazon EC2 Container Registry (ECR)", "Amazon ECR") \
               .replace("- Other", "(Other)") \
               .replace("- Compute", "(Compute)")


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
    ('subject', 'aws-bills'),
    ('content', message)
]

response = requests.post(ZULIP_URL, data=data,
                         auth=(ZULIP_BOT_EMAIL, ZULIP_BOT_TOKEN))

cost_blocks = {
    "type": "section",
    "fields": []
}

other = total

for s in spendings[:BREAKDOWN_COUNT]:
    if s[0] < 1.00:
        continue

    cost_blocks['fields'] += [{
        'type': 'mrkdwn',
        'text': f'*{s[1]}:* ${s[0]:.2f}'
    }]

    other -= s[0]

if other > 0.001:
    cost_blocks['fields'] += [{
        'type': 'mrkdwn',
        'text': f'*Other:* ${other:.2f}'
    }]

slack_message = {
    "blocks": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Yesterday, you spent *${total:.2f}* on AWS. Here's the breakdown:"
            }
        },
        {
            "type": "divider"
        },
        cost_blocks,
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "{start}".format(start=start_date.strftime("%b %d, %Y"))
                }
            ]
        },
        {
            "type": "divider"
        }
    ]
}

response = requests.post(SLACK_URL, json=slack_message)
print(response)
