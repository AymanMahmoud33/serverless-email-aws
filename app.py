import os
import email
import logging

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3  = boto3.client("s3")
ses = boto3.client("ses")

FORWARD_TO    = os.environ["FORWARD_TO"]
FORWARD_FROM  = os.environ["FORWARD_FROM"]
BUCKET_NAME   = os.environ["BUCKET_NAME"]
BUCKET_PREFIX = os.environ["BUCKET_PREFIX"]  # "inbox/"

# These headers are tied to the original message signature.
# Keeping them causes DKIM failure on the forwarded copy.
HEADERS_TO_REMOVE = [
    "DKIM-Signature",
    "Sender",
    "Return-Path",
    "Message-ID",
]


def lambda_handler(event, context):
    for record in event["Records"]:
        mail    = record["ses"]["mail"]
        receipt = record["ses"]["receipt"]

        msg_id     = mail["messageId"]
        recipients = receipt["recipients"]
        s3_key     = f"{BUCKET_PREFIX}{msg_id}"

        logger.info("Processing %s for recipients %s", msg_id, recipients)

        raw = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)["Body"].read()
        msg = email.message_from_bytes(raw)

        original_from    = msg.get("From", "unknown")
        original_subject = msg.get("Subject", "(no subject)")

        for header in HEADERS_TO_REMOVE:
            if header in msg:
                del msg[header]

        # Rewrite From so SES accepts the send
        if "From" in msg:
            msg.replace_header("From", FORWARD_FROM)
        else:
            msg["From"] = FORWARD_FROM

        # Reply-To preserves the original sender — your team hits Reply
        # and it goes back to the person who sent it, not to your relay address
        if "Reply-To" in msg:
            msg.replace_header("Reply-To", original_from)
        else:
            msg["Reply-To"] = original_from

        # Subject prefix tells you which alias received it
        original_recipient = recipients[0] if recipients else ""
        new_subject = f"[{original_recipient}] {original_subject}"
        if "Subject" in msg:
            msg.replace_header("Subject", new_subject)
        else:
            msg["Subject"] = new_subject

        if "To" in msg:
            msg.replace_header("To", FORWARD_TO)
        else:
            msg["To"] = FORWARD_TO

        ses.send_raw_email(
            Source=FORWARD_FROM,
            Destinations=[FORWARD_TO],
            RawMessage={"Data": msg.as_bytes()},
        )
        logger.info("Forwarded %s → %s → %s", msg_id, original_recipient, FORWARD_TO)

    return {"statusCode": 200}
