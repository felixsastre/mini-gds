# Technical reference

How to use the library from code. The [README](README.md) explains what it is for.

## Use

```python
from inventory_nesting import Inventory, Nesting

# Authorizations are an ordered mapping: the order is the hierarchy, highest class first.
inventory = Inventory({"Y": 420, "B": 385, "M": 300})
inventory.load_bookings({"Y": 10, "B": 20, "M": 30})
inventory.availability("M", Nesting.NET)  # 300 - 30 = 270, never above the class above
inventory.sell("M", 5, Nesting.THRESHOLD)  # SaleRejectedError if the class cannot sell 5 seats
```

Pass the classes in another order and net nesting caps each class by the wrong one, without any error.
