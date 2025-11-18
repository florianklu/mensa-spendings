# Mensa Spendings

Have you ever wondered how much you actually spend on your daily coffee? Or on that delicious dessert after lunch?
In theory, you could check this on the *Delicard online service* website [1]. 
But there's a catch: the website only shows the last 90 days, there’s no download option, and you can’t run any further analysis.

With this project, you can now easily download your data from the *Delicard online service*, collect it for a longer period of time and analyze it with **Pandas** in a **Jupyter notebook** or in a spreadsheet editor of your choice to gain a clearer understanding of your spending habits!

*[1] https://kartenservice.studentenwerk-pb.de/KartenService/index.html*

## Installation
```
pip install -r requirements.txt
```

## Usage

Run the the download function at least every 90 days:
```bash
python delicardservice.py --cardNr <card number> --password <password>
```
or execute `scrapeDelicardApi(<card number, <password>)` in the Jupyter notebook.
The `card number` is a 6 digit number printed on your DeliCard. The `password` can be found on the receipt you received together with your DeliCard. If you can't find the receipt anymore, you could request new a password at the Studierendenwerk service office, but I haven't tried that yet.


```python
import pandas as pd
import delicardservice as ds

cardNr = "123456" # the number printed on your delicard
password = "Pswd" # from the receipt you got with your card or from a cashier

ds.scrapeDelicardApi(cardNr, password)
ds.mergeDataDumps(cardNr)

data: pd.DataFrame = ds.getDataframe(cardNr)

# ...
```

## Features
- Download JSON data files from the Delicard Service API (limited to last 90 days)
- Merge data from different time periods to create a dataset with information from more than 90 days
- Convert the data into easy-to-read CSV files and Pandas DataFrames
- Cache server responses to avoid unnecessary load on the server