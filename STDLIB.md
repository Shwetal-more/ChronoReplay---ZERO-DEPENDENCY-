# STDLIB Substitutions

This project uses only Python's standard library.
**Third-party dependencies: 0**

| # | Normally Used        | Standard Library Replacement     | Purpose                  |
| - | -------------------- | -------------------------------- | ------------------------ |
| 1 | Pydantic             | `dataclasses`                    | Event models             |
| 2 | JSON libraries       | `json`                           | JSON serialization       |
| 3 | UUID packages        | `uuid`                           | Unique event IDs         |
| 4 | Date/time packages   | `datetime`                       | UTC timestamps           |
| 5 | Schema validators    | `isinstance` + custom validation | Field/type validation    |
| 6 | Enum/choice packages | `set`                            | Allowed-value validation |

**Tradeoff:** We implement validation and schema rules ourselves instead of relying on third-party frameworks.
