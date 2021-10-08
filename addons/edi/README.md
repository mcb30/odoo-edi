# EDI Gateway

## Safety Catch

In order to allow the edi notifier to send out emails:
- A safety catch needs to be set on the edi notifier
- This same safety catch needs to be configured on the odoo config file and return a truthy value
```
[email]
edi_notifier_safety_catch=True
```
- If no safety is configured no emails will be sent
- If only one part of the safety is configured no emails will be sent

