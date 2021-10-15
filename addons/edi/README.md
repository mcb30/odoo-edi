# EDI Gateway

## Safety Catch

In order to allow edi files to be transfered:
- A safety catch needs to be set on the EDI gateway.
- This same safety catch needs to be configured on the odoo config file and return a truthy value.
```
[edi]
edi_gateway_safety_catch=True
```
- If no safety is configured no files will be sent
- If only one part of the safety is configured no files will be sent
