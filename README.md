# Mensa-Guru

Have you always been asking yourself how much you actually spend on your daily coffee? Or that delicious dessert after lunch?
Theoretically, you could see that on the *Delicard online service* website [1]. 
But there is a catch: the web interface only shows the last 90 days, a quick export is not possible, nor are further evaluations.

With this project you can now easily download your data from the *Delicard online service*, collect it and analyse it with a **Jupyter notebook** and **Pandas** or **MS Excel** to get a better understanding of your spending habits!

*[1] https://kartenservice.studentenwerk-pb.de/KartenService/index.html*

## Installation
```
pip install -r requirements.txt
```

## Usage

```python
import pandas as pd
import delicardservice as ds

cardNr = "123456" # the number printed on your delicard
password = "Pswd" # from the receipt you got with your card or from a cashier

ds.scrapeDelicardApi(cardNr, password)
ds.mergeDataDumps(cardNr)

data: pd.DataFrame = ds.getDataframe(cardNr)
```
```python
import matplotlib.pyplot as plt

# ...
```

## Features
- Downloading json data files from Delicard Service
- Merging data from different time periods so that the data can be collected for more than 90 days
- Conversion of the data into easily readable csv files and Pandas DataFrames
- Caching of server responses to avoid unnecessary load on the server
