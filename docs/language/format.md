
# Format

APPL provides utilities to format prompt generation.

Consider the following example, formatting directives are represented as `with` contexts:

```python
@ppl
def list_place():
    "Please list some interesting places to go in Toronto:"
    with LetterList(indent=INDENT):
        "Restaurant"
        with IndentedList(indexing="star"):
            for _ in range(2):
                f" {gen(temperature=0.7, stop=NEWLINE)}"
        "Museum"
        with IndentedList(indexing="star"):
            for _ in range(2):
                f" {gen(temperature=0.7, stop=NEWLINE)}"
    return records()
```

The above code generates the following output:

```plaintext
>>> list_place()
Please list some interesting places to go in Toronto:
a. Restaurant
    * Canoe
    * Bar Isabel
b. Museum
    * Royal Ontario Museum
    * Art Gallery of Ontario
```

Below is a list of supported formatting classes APPL provides:

| **Class Name**        | **Description**                                           | **Example Output**                                                                              |
| --------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `LineSeparated`       | Base class for line-separated lists.                      | Item1<br>Item2<br>Item3                                                                         |
| `DoubleLineSeparated` | Base class for double line-separated lists.               | Item1<br><br>Item2<br><br>Item3                                                                 |
| `IndentedList`        | LineSeparated list with increased indentation.            | &nbsp;&nbsp;&nbsp;&nbsp;Item1<br>&nbsp;&nbsp;&nbsp;&nbsp;Item2<br>&nbsp;&nbsp;&nbsp;&nbsp;Item3 |
| `NumberedList`        | LineSeparated list with numbered indexing.                | 1. Item1<br>2. Item2<br>3. Item3                                                                |
| `LowerLetterList`     | LineSeparated list with lowercase letter indexing.        | a. Item1<br>b. Item2<br>c. Item3                                                                |
| `UpperLetterList`     | LineSeparated list with uppercase letter indexing.        | A. Item1<br>B. Item2<br>C. Item3                                                                |
| `LowerRomanList`      | LineSeparated list with lowercase Roman numeral indexing. | i. Item1<br>ii. Item2<br>iii. Item3                                                             |
| `UpperRomanList`      | LineSeparated list with uppercase Roman numeral indexing. | I. Item1<br>II. Item2<br>III. Item3                                                             |
| `DashList`            | LineSeparated list with dashes as indexing markers.       | - Item1<br>- Item2<br>- Item3                                                                   |
| `StarList`            | LineSeparated list with stars as indexing markers.        | \* Item1<br>\* Item2<br>\* Item3                                                                |
| `LetterList`          | Alias for LowerLetterList.                                | a. Item1<br>b. Item2<br>c. Item3                                                                |
| `RomanList`           | Alias for LowerRomanList.                                 | i. Item1<br>ii. Item2<br>iii. Item3                                                             |
