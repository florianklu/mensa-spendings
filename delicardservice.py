import json
import os
from datetime import date, timedelta
from time import time, sleep
import requests_cache
from requests.exceptions import HTTPError
import pandas as pd
import glob

def scrapeDelicardApi(cardNr: str, password: str, days: int = 90, forceReload = False) -> None:
    """
    Fetches position, transaction and card data from the delicard service api and saves it to the folder <cardNr>/<data category>_<date>.json
    Currently saves autoload information and transactions consisting of positions (booking items).
    Data is cached for 24 hours to reduce the number of requests to the server.

    Args:
        cardNr: DeliCard number
        password: Password from the Kartenservice
        days (default=90): Number of days before today for which the payment data is requested (limited to last 90 days by the server)
        forceReload (default=False): If True, the cache is ignored and fresh data is requested from the server.
    """

    def getMs() -> str:
        """Returns the current unix time in milliseconds as a string."""
        return str(int(round(time() * 1000)))
    
    def checkResponse(response):
        try: 
            response.raise_for_status()
            print(f"{response}")
        except HTTPError as e:
            print(f"Error: Request to {e.response.url} failed. Status code: {e.response.status_code}. Check your username and password. Server might also be in maintanace.")
    
    s = requests_cache.CachedSession(cache_name="delicard_api_cache", ignored_parameters=['_', 'authToken'], allowable_codes=(200,201), allowable_methods=('GET', 'POST'), expire_after=24*3600)
    
    if forceReload:
        s.cache.clear()
    
    s.headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                "dnt": "1", 
                "x-requested-with": 
                "XMLHttpRequest"}
    s.auth = ("KASVC", "zKv5yE1LZUmvW29I")  # well, this password is hard coded in the frontend

    # Parameters for purchasing history data
    # Example (only the last 90 days can be fetched from the server):
    # dateFrom = "02.01.2023"
    # dateTo = "28.02.2023"
    format = "%d.%m.%Y"
    now = date.today() + timedelta(days=1)
    dateFrom = (now - timedelta(days=days-1)).strftime(format)
    dateTo = now.strftime(format)
    
    params = {"format": "JSON", "karteNr": cardNr, "datumVon": dateFrom, "datumBis": dateTo}
    caching_check_transpos = requests_cache.Request("GET", "https://kartenservice.studentenwerk-pb.de/TL1/TLM/KASVC/TRANSPOS", params=params)
    caching_check_trans = requests_cache.Request("GET", "https://kartenservice.studentenwerk-pb.de/TL1/TLM/KASVC/TRANS", params=params)
    data_requests_are_cached = s.cache.contains(request=caching_check_transpos) and s.cache.contains(request=caching_check_trans)
    
    # if we need data that is not in cache, we have to login on the server first
    if not data_requests_are_cached:
        with s.cache_disabled():
            print("Logging in...")
            # don't know what this does
            clientReg = s.post("https://kartenservice.studentenwerk-pb.de/TL1/TLA/ClientReg", params={"ClientID": "20", "RegKey": "4G3hQj7E5ivIzbXNlt4Eu8rLvRb3Dy4g", "format": "JSON", "datenformat": "JSON"})
            checkResponse(clientReg)

            # Texts for the UI describing the attributes from the API Response. The Kartenservice website makes this request, too.
            textres = s.get("https://kartenservice.studentenwerk-pb.de/TL1/TLM/KASVC/TEXTRES", params={"LangId": "de-DE", "format": "JSON", "_": getMs()})
            checkResponse(textres)

            # Log In to the server, response is a json document containing the session key (authToken)
            login = s.post("https://kartenservice.studentenwerk-pb.de/TL1/TLM/KASVC/LOGIN", params={"karteNr": cardNr, "format": "JSON", "datenformat": "JSON"}, json={"BenutzerID":cardNr,"Passwort":password})
            checkResponse(login)
            j = json.loads(login.text)
            authToken = j[0]["authToken"]

            karte = s.get("https://kartenservice.studentenwerk-pb.de/TL1/TLM/KASVC/KARTE", params={"format": "JSON", "authToken": authToken, "karteNr": cardNr, "_": getMs()})
            checkResponse(karte)
    else:
        print("Data already cached...")
        authToken = "" # dummy value, won't be send to server

    # Fetches information about the autoload feature (Lastschriftmandat)


    sleep(2.3)

    # Purchasing history data
    # Fetch the booking positions from all transactions. A transaction may include multiple positions.
    transposData = s.get("https://kartenservice.studentenwerk-pb.de/TL1/TLM/KASVC/TRANSPOS", params={"format": "JSON", "authToken": authToken, "karteNr": cardNr, "datumVon": dateFrom, "datumBis": dateTo, "_": getMs()})
    checkResponse(transposData)

    # Fetch all transactions. Transaction data includes only payment information, nothing about positions.
    transactionData = s.get("https://kartenservice.studentenwerk-pb.de/TL1/TLM/KASVC/TRANS", params={"format": "JSON", "authToken": authToken, "karteNr": cardNr, "datumVon": dateFrom, "datumBis": dateTo, "_": getMs()})
    checkResponse(transactionData)
    
    # create a folder for every account and store data in new files
    if not os.path.exists(cardNr):
        os.makedirs(cardNr)
    with open(f"{cardNr}/positions_{now}_{days}.json", "w+", encoding="utf-8") as f:
        f.write(transposData.text)
    with open(f"{cardNr}/transactions_{now}_{days}.json", "w+", encoding="utf-8") as f:
        f.write(transactionData.text)
    if not data_requests_are_cached:
        with open(f"{cardNr}/karte.json", "w+", encoding="utf-8") as f:
            f.write(karte.text)
    print("Data download successful!")

def mergeDataDumps(cardNr: int, clean: bool= False) -> dict[str, pd.DataFrame]:
    """
    Adds transactions and positions from json data dumps duplication-free into a database (csv-files)
    Args:
        cardNr: DeliCard number
        clean (default=False): If True, the json data dumps are deleted after merging
    
    Example `transaction`:
    transFullId               datum     ortName        kaName  typName  zahlBetrag
     10-3419-37 2022-12-08 11:36:00   Cafeteria  Cafeteria 10  Verkauf        -3.5

    Example `position`:
    transFullId  posId                  name  menge  epreis  gpreis  rabatt
     10-3419-37      3   Brötchen mit Salami      1     1.3     1.3     NaN
    """
    dataframes : dict[str, pd.DataFrame] = {
        "transactions": [],
        "positions": []
        }
    for table in dataframes.keys():
        # Find paths of new files
        paths = glob.glob(f"{cardNr}/{table}_*.json")
        for path in paths:
            df = pd.read_json(path, precise_float=True, encoding="utf-8")
            if table == "transactions":
                df["datum"] = pd.to_datetime(df["datum"], format="%d.%m.%Y %H:%M")
                df.drop(["id","mandantId"], axis=1, inplace=True)
            elif table == "positions":
                df.drop(["id","mandantId", "bewertung"], axis=1, inplace=True)
            dataframes[table].append(df)
        
        # open files and save data as a list of pandas dataframes
        try:
            if table == "transactions":
                dataframes[table].append(pd.read_csv(f"{cardNr}/{table}.csv", encoding="utf-8", parse_dates=["datum"]))
            elif table == "positions":
                dataframes[table].append(pd.read_csv(f"{cardNr}/{table}.csv", encoding="utf-8"))
        except (pd.errors.EmptyDataError, FileNotFoundError):
            print(f"No data found in {table} csv database file, skipping...")

        # merge all dataframes together and save them as a csv file
        dataframes[table] = pd.concat(dataframes[table]).drop_duplicates()
        if table == "transactions":
            dataframes[table].sort_values(by=["datum"], inplace=True)
        dataframes[table].to_csv(f"{cardNr}/{table}.csv", mode="w+", encoding="utf-8", index=False)

        # if we reached this line, the json files have been merged successfully and we can clean up the folder
        if clean:
            for path in paths: os.remove(path)
    return dataframes

def getDataframe(cardNr: int, transactions: pd.DataFrame = None, positions:pd.DataFrame = None) -> pd.DataFrame:
    """
    Combines transaction and position data by joining both datasets on the transFullId attribute.
    Returns a Pandas DataFrame, which is also saved as a csv file (fullData.csv)
    Before calling this function, the json data dumps have to be merged into (positions.csv, transactions.csv)! 

    Args:
        cardNr: DeliCard number
        transactions (default=None): If set, the transactions DataFrame is used instead of the transactions.csv file
        positions (default=None): If set, the positions DataFrame is used instead of the positions.csv file
    
    Example:
                                    datum    ortName        kaName  typName  zahlBetrag                  name  menge  epreis  gpreis  rabatt
    transFullId posId
    10-3419-37  3     2022-12-08 11:36:00  Cafeteria  Cafeteria 10  Verkauf        -3.5   Brötchen mit Salami      1     1.3     1.3     NaN   
    """
    try:
        if not transactions:
            transactions = pd.read_csv(f"{cardNr}/transactions.csv", encoding="utf-8", parse_dates=["datum"])
        if not positions:
            positions = pd.read_csv(f"{cardNr}/positions.csv", encoding="utf-8")
        merged_df = pd.merge(transactions, positions, how="outer", on="transFullId")
        merged_df.sort_values(by=["datum","posId"], inplace=True)
        merged_df.set_index(["transFullId","posId"], inplace=True)
    except FileNotFoundError:
        print("No data found in csv database files, please run mergeDataDumps() first!")
        return
    # write merged (unified) data to csv for excel analysis
    merged_df.to_csv(f"{cardNr}/fullData.csv", mode="w+", encoding="utf-8")
    return merged_df

if __name__ == "__main__":
    cardNr = input("CardNr:")
    password = input("Password:")
    print("Downloading all available data from API and saving it to files...")
    scrapeDelicardApi(cardNr, password)