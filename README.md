# serverless-email-aws

Serverless email infrastructure using Amazon SES, Lambda, and S3.  
Catch all mail at your domain, store it durably, forward it — fully automated with one SAM deploy.

> 📖 Read the full write-up: [Stop Paying $20/Month for Email You Could Run for $1.50](https://dev.to/aws-builders/i-replaced-my-email-server-with-3-aws-services-and-pay-150month-2eej)

---

## What this does

- **Receives** all email sent to `@yourdomain.com` via SES receipt rules
- **Stores** every raw message in S3 (`inbox/`) with 30-day auto-expiry
- **Forwards** to any address with correct headers, DKIM-safe re-sending, and original `Reply-To` preserved
- **Provisions** all DNS records (MX, SPF, DMARC, DKIM CNAMEs) automatically in Route 53
- **Activates** the SES receipt rule set automatically — no manual steps after deploy

<img width="800" height="533" alt="image" src="https://github.com/user-attachments/assets/57ac3f5e-d64d-4fee-8012-56d63d614e33" />


---

## Prerequisites

| Tool | Version |
|---|---|
| AWS CLI | v2.x |
| SAM CLI | v1.129+ |
| Python | 3.12+ |
| Domain in Route 53 | — |

---

## Quick start

**1. Clone the repo**
```bash
git clone https://github.com/AymanMahmoud33/serverless-email-aws.git
cd serverless-email-aws
```

**2. Get your Route 53 hosted zone ID**
```bash
aws route53 list-hosted-zones \
  --query "HostedZones[?Name=='yourdomain.com.'].{Id:Id,Name:Name}"
```

**3. Build and deploy**
```bash
sam build
sam deploy --guided \
  --parameter-overrides \
    EmailDomain=yourdomain.com \
    ForwardTo=you@gmail.com \
    ForwardFrom=relay@yourdomain.com \
    HostedZoneId=ZXXXXXXXXXXXXX
```

**4. Request SES production access**

New AWS accounts are sandboxed by default. Go to:  
**SES Console → Account dashboard → Request production access**

AWS typically responds within 24 hours.

**5. Test it**
```bash
# Watch logs while you send a test email
aws logs tail /aws/lambda/YOUR_STACK_NAME-ProcessEmailFunction \
  --follow \
  --region us-east-1
```

---

## Parameters

| Parameter | Description | Example |
|---|---|---|
| `EmailDomain` | Domain to receive email at | `yourdomain.com` |
| `ForwardTo` | Where forwarded mail lands | `you@gmail.com` |
| `ForwardFrom` | Verified SES sender (From header) | `relay@yourdomain.com` |
| `HostedZoneId` | Route 53 hosted zone ID | `Z1234ABCDE` |

---

## Project structure

```
├── template.yaml        # SAM template — all infrastructure
├── src/
│   └── app.py           # Lambda — receives, processes, forwards
├── samconfig.toml       # SAM deploy defaults (git-ignored, see example)
└── samconfig.toml.example
```

---

## Receiving to a specific address only

By default, the receipt rule catches **all** mail at your domain. To restrict to specific addresses, update the `Recipients` field in `template.yaml`:

```yaml
ReceiptRule:
  Rule:
    Recipients:
      - info@yourdomain.com
      - support@yourdomain.com
```

Any address not on the list will be rejected with `550 5.1.1`.

---

## Routing different aliases to different people

Add a routing table inside `src/app.py`:

```python
ROUTING = {
    "info@yourdomain.com":    "team@yourdomain.com",
    "support@yourdomain.com": "helpdesk@yourdomain.com",
}

forward_to = ROUTING.get(recipients[0], FORWARD_TO)
```

---

## Troubleshooting

**Domain verification stuck on Pending**

Check that DNS is resolving:
```bash
nslookup -type=CNAME YOUR_DKIM_TOKEN._domainkey.yourdomain.com 8.8.8.8
```

If it resolves, nudge SES to recheck:
```bash
aws ses verify-domain-identity --domain yourdomain.com --region us-east-1
aws ses get-identity-verification-attributes --identities yourdomain.com --region us-east-1
```

**Emails arriving from wrong forwarder**

SES only allows one active receipt rule set per region per account. If you have multiple environments, check which rule set is active:
```bash
aws ses describe-active-receipt-rule-set --region us-east-1 --query "Metadata.Name"
```

---

## Not a replacement for mailboxes

This stack handles **programmatic email** — aliases, contact forms, automated sends. It is not a replacement for Google Workspace or AWS WorkMail. Keep those for your team's human inboxes; use this for everything your application touches.

---

## License

MIT
