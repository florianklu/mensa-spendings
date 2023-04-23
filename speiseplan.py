import requests_cache
import requests
from bs4 import BeautifulSoup as bs
from datetime import date, timedelta
from time import sleep

requests_cache.install_cache('speiseplan_cache', backend='sqlite', expire_after=timedelta(hours=2))

def parse_menu_plan(html):
    soup = bs(html, 'html.parser')
    establishment = soup.find("div", class_="main-content").find("div", class_="row")
    establishment = establishment.findChild().findChild().findChild().text.strip()
    
    table_dishes = soup.find_all("table", class_="table-dishes") # all available categories like main dishes, side dishes, soups and desserts

    onlineplan = soup.find("div", class_="pa-mensa-onlineplan")
    alert_danger = onlineplan.findChild("div", class_="alert alert-danger", recursive=False) # recursive = False -> only look for mensa closures
    if alert_danger or (len(table_dishes) == 0):
        print("Speiseplan konnte nicht abgerufen werden.")
        if alert_danger: print(str(alert_danger.text).strip()) 
        else: print("Parsingfehler")
    categories = []
    for t in table_dishes:
        categories.append(_parse_category(t))
    return establishment, categories

def _parse_category(t):
    # main dishes, side dishes, soups and desserts have their own table
    category_name = t.find_previous("h3").text
    rows = t.find_all("tr")
    dishes = []
    # data for a meal is splitted in blocks of two table rows, 
    # with an empty row between meals (odd, even, spacer)
    for i in range(0, len(rows), 3):
        description_tag = rows[i] # odd class
        dish_name = str(description_tag.div.h4.text).strip()
        prices = description_tag.find_all("div", class_="price")
        prices = [(str(price.strong.text)[:-1], str(price.strong.next_sibling).strip()) for price in prices]
        # prices = [(group, price), (...), ...]
        prices = dict(prices)
        buttons = description_tag.find("div", class_="buttons") # vegetarian, vegan,...
        buttons = [button["title"] for button in buttons.find_all("img")]
        try:
            images : bs= description_tag.picture
            image_s = "https://www.studierendenwerk-pb.de/" + images.find("source", media="(max-width: 400px)")["srcset"]
            image_l = "https://www.studierendenwerk-pb.de/" + images.find("source", media="(max-width: 768px)")["srcset"]
        except:
            image_s = image_l = None
        ingredients = []
        nutritions = {}
        try: 
            details = rows[i+1] # even class
            details = details.find("div", class_="ingredients-list")
            ingredients_tag = details.find("div", class_="ingredients") # <div class="col-sm-6 ingredients">
            nutritions_tag = details.find("div", class_="nutritions") # <div class="col-sm-6 nutritions">
            if not ingredients_tag.find("div", class_="alert alert-danger"):
                br_tags = ingredients_tag.find_all("br")
                ingredients = list(filter(None,[br.previous_sibling.strip() for br in br_tags]))
            if not nutritions_tag.find("div", class_="alert alert-danger"):
                br_tags = nutritions_tag.find_all("br")
                nutritions = list(filter(None,[br.previous_sibling.strip() for br in br_tags]))
                nutritions = dict([nutrition.split(" = ") for nutrition in nutritions])
        except:
            print("Fehler beim Parsen der Inhaltsstoffe und Nährwerte.")
        dish = Dish(dish_name, prices, buttons, ingredients, nutritions, image_s, image_l)
        dishes.append(dish)
    category = Category(category_name, dishes)
    return category

def download_menu(restaurant, req_date):
    """Downloads the html from the menu page of a restuarant."""
    s = requests.Session()
    s.headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
    sleep(0.2)
    r = s.get(f"https://www.studierendenwerk-pb.de/gastronomie/speiseplaene/{restaurant}/", params={"tx_pamensa_mensa[date]": str(req_date)})
    return r.content

## Models
class Dish:
    """A dish with its name, prices, dietary suitability, ingredients, nutritions and images."""
    def __init__(self, name: str, prices: dict, buttons : list[str], ingredients: list[str], nutritions: dict,
                  image_s: str = None, image_l: str = None):
        self.name = name
        self.prices = prices
        self.buttons = buttons
        self.ingredients = ingredients
        self.nutritions = nutritions
        self.image_s = image_s
        self.image_l = image_l
    def __str__(self):
        text = self.name
        if self.buttons:
            text += "\n   (" + ", ".join(self.buttons) + ")"
        text += "\n    Preise:"
        text += "".join([f"\n       - {g}: {self.prices[g]}" for g in self.prices.keys()])
        text += "\n    Nährwerte:"
        text += "".join([f"\n       - {n}: {self.nutritions[n]}" for n in self.nutritions.keys()])
        text += "\n    Inhaltsstoffe:"
        text += "".join([f"\n       - {i}" for i in self.ingredients])
        text += "\n    Bild:"
        text += f"\n       - klein: {self.image_s}"
        text += f"\n       - groß: {self.image_l}"
        return text
    
class Category:
    """A category of dishes, e.g. "Hauptgerichte" or "Beilagen"."""
    def __init__(self, name: str, dishes: list[Dish]):
        self.name = name
        self.dishes = dishes
    def __str__(self):
        text = f"\n### {self.name} ###\n"
        for num, dish in enumerate(self.dishes):
            text += f"\n{num+1}) {dish}"
        return text


    
restaurants_urls = ["mensa-forum","mensa-academica", "cafete", "bona-vista", "grillcafe", "mensa-zm2", "mensa-basilica-hamm", "mensa-atrium-lippstadt"]

def get_menu_plan(restaurant, req_date):
    """Returns the menu plan of a restaurant for a given date."""
    if restaurant not in restaurants_urls:
        raise ValueError(f"Restaurant {restaurant} not found.")
    content = download_menu(restaurant, req_date)
    establishment, categories = parse_menu_plan(content)
    return establishment, categories

def print_menu_plan(restaurant, req_date):
    """Prints the menu plan of a restaurant for a given date."""
    establishment, categories = get_menu_plan(restaurant, req_date)
    heading = establishment + " - " + date.strftime(req_date, "%d.%m.%Y")
    print(len(heading)*"-"*2)
    print(int(len(heading)/2)*" " + heading)
    print(len(heading)*"-"*2)
    for c in categories:
        print(c)
        
if __name__ == "__main__":
    """Print menus for all restaurants for tomorrow."""
    for restaurant in restaurants_urls:
        req_date = date.today()+ timedelta(days = 1)
        print_menu_plan(restaurant, req_date)

