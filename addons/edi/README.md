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

# Model helpers
## add_if_not_exists()
To be used as a decorator, as an easy way to patch functions into models.
### Usage
```python
from odoo.addons.edi.models import add_if_not_exists
from odoo import models

@add_if_not_exists(models.BaseModel)
def some_function(self):
    print("some_function() is callable from all odoo models now!")
```

## add_even_if_exists()
To be used as a decorator, as an easy way to override functions in models.

### Usage
```python
from odoo.addons.edi.models import add_if_not_exists
from odoo import models

@add_even_if_exists(models.BaseModel)
def write(self):
    print("write() on all models now prints stuff out instead of writing to the db!")
```

## sliced()
Return the recordset `self` split into slices of a specified size
### Usage
```python
print(my_recordsets)
> stock.move.line(1,2,3,4,5)
for sliced_recs in my_recordsets.sliced(size=2):
    print(sliced_recs)
> stock.move.line(1,2)
> stock.move.line(3,4)
> stock.move.line(5,)
```

## batched()
Return the recordset `self` split into batches of a specified size
### Usage
```python
print(my_recordsets)
> stock.move.line(1,2,3,4,5)
for r, batch in my_recordsets.batched(size=2):
    print(f"Processing move lines {r[0] + 1}-{r[-1] + 1} of {len(my_recordsets)}")
    print(batch)
> Processing move lines 1-2 of 5
> stock.move.line(1,2)
> Processing move lines 3-4 of 5
> stock.move.line(3,4)
> Processing move lines 5-5 of 5
> stock.move.line(5,)
```

## groupby()
Return the recordset `self` grouped by `key`

The recordset will automatically be sorted using `key` as the sorting key, unless `sort` is explicitly set to `False`.

`key` is permitted to produce a singleton recordset object, in which case the sort order will be well-defined but arbitrary. If a non-arbitrary ordering is required, then use :meth:`~.sorted` to sort the recordset first, then pass to :meth:`~.groupby` with `sort=False`.
### Usage
```python
print(my_recordsets)
> stock.move.line(1,2,3,4)
for product, move_lines in my_recordsets.groupby("product_id"):
    print(product.name)
    print(move_lines)
> "Angry Aubergine"
> stock.move.line(1,2)
> "Benevolent Banana"
> stock.move.line(3,4)
```

## statistics()
Gather profiling statistics for an operation
### Usage
```python
with self.statistics() as stats:
    # do something
_logger.info(f"Took {stats.elapsed} seconds, did {stats.count} queries")
```

## trace()
Trace database queries
