import requests
from lxml import html
import re
import time
import json
import os.path

conservationCodes = { "not evaluated": "NotEvaluated", "data deficient":"DataDeficient",  "least concern":"LeastConcern",
                      "near threatened":"NearThreatened", "conservation dependent":"ConservationDependent",
                      "vulnerable":"Vulnerable", "endangered":"Endangered", "threatened":"Endangered", "critically endangered":"CriticallyEndangered",
                      "extinct in the wild":"ExtinctInTheWild", "extinct":"CompletelyExtinct" }

json_filename = "data/azanimals.txt"

diets = []
habitats = []
groups = []
eats = []
animals = []
predators =[]

def load_data():
    file = open(json_filename)
    data = json.load(file)
    return data

def save_data(data):
    with open(json_filename, 'w') as outfile:
        json.dump(data, outfile)


def fix_diet():
    file = open(json_filename)
    data = json.load(file)
    for animal in data["animals"]:
        if animal.get("diet"):
            animal["diet"] = animal["diet"][0]

    with open(json_filename, 'w') as outfile:
        json.dump(data, outfile)


def fix_genus():
    file = open(json_filename)
    data = json.load(file)
    for animal in data["animals"]:
        if 'taxon_name' in animal.keys() and re.match('genus ', animal["taxon_name"]):
            animal["taxon_name"] = animal["scientific_name"] = animal["taxonomy"]["genus"]
            animal["taxon_rank"] = 'genus'
            animal['taxonomy'].pop('species', None)

    with open(json_filename, 'w') as outfile:
        json.dump(data, outfile)

def fix_names():
    file = open(json_filename)
    data = json.load(file)

    file = open(json_filename)
    backup = json.load(file)

    for animal in data["animals"]:
        animal["english_name"] = animal["english_name"].lower().strip()
        others = []

        animal.pop("other_names", None)
        for tmp in backup["animals"]:
            if 'scientific_name' in tmp.keys() and 'other_names' in tmp.keys() and tmp["scientific_name"].lower() == animal["scientific_name"]:
                animal["other_names"] = tmp["other_names"]

        if 'other_names' in animal.keys():
            for name in animal["other_names"] :
                name = re.sub('([a-z^])([A-Z])', lambda pat: pat.group(1)+' '+pat.group(2).lower(), name)
                others.append(name.lower().strip())
        animal["other_names"] = others

    with open(json_filename, 'w') as outfile:
        json.dump(data, outfile)

def fix_taxon_case():
    file = open(json_filename)
    data = json.load(file)
    for animal in data["animals"]:
        for key in animal["taxonomy"]:
            animal["taxonomy"][key] = animal["taxonomy"][key].lower().strip().replace('_', ' ')
        if 'taxon_name' in animal.keys():
            animal["scientific_name"] = animal["taxon_name"] = animal["taxon_name"].lower().strip().replace('_', ' ')

    with open(json_filename, 'w') as outfile:
        json.dump(data, outfile)

def fix_genus_taxon():
    english_names = ["swan", "alligator", "camel", "opossum", "fox", "hyena", "lemming", "chipmunk", "mouse", "echidna",
                     "quoll", "jackal", "hamster", "skunk", "badger", "kangaroo", "bison", "wildebeest", "beever", "anteater",
                     "rat", "wombat", "hedgehog", "hare", "chinchilla", "warthog", "swan"]
    file = open(json_filename)
    data = json.load(file)
    for animal in data["animals"]:
        if (animal["english_name"] in english_names):
            animal["taxon_rank"] = "genus"
            animal["taxon_name"] = animal["taxonomy"]["genus"]
            animal["scientific_name"] = animal["taxon_name"]
            animal["taxonomy"].pop("species", None)

    with open(json_filename, 'w') as outfile:
        json.dump(data, outfile)

def fix_numeric_data():
    file = open(json_filename)
    data = json.load(file)
    for animal in data["animals"]:
        if "length" in animal["numerics"].keys():
            animal["numerics"]["length"] = getLength(animal["numerics"]["length"])
        if "height" in animal["numerics"].keys():
            animal["numerics"]["height"] = getHeight(animal["numerics"]["height"])
        if "life span" in animal["numerics"].keys():
            animal["numerics"]["life span"] = getLifespan(animal["numerics"]["life span"])
        if "top speed" in animal["numerics"].keys():
            value = getTopSpeed(animal["numerics"]["top speed"])
            if (not value):
                print("Removing invalid top speed:"+animal["numerics"]["top speed"])
                animal["numerics"].pop("top speed", None)
            else:
                animal["numerics"]["top speed"] = value

        if animal["scientific_name"] != 'unknown' and animal["scientific_name"] != animal["taxon_name"]:
            animal["taxon_name"] = animal["scientific_name"]
            if animal["taxon_rank"] == 'genus':
                animal["taxon_rank"] = 'species'
            elif animal["taxon_rank"] == 'family':
                animal["taxon_rank"] = 'genus'
            elif animal["taxon_rank"] == 'order':
                animal["taxon_rank"] = 'family'
            elif animal["taxon_rank"] == 'class':
                animal["taxon_rank"] = 'order'

    with open(json_filename, 'w') as outfile:
        json.dump(data, outfile)

def fix_taxon_rank_name():
    file = open(json_filename)
    data = json.load(file)
    for animal in data["animals"]:
        if animal["scientific_name"] != 'unknown' and animal["scientific_name"] != animal["taxon_name"]:
            animal["taxon_name"] = animal["scientific_name"]
            if animal["taxon_rank"] == 'genus':
                animal["taxon_rank"] = 'species'
            elif animal["taxon_rank"] == 'family':
                animal["taxon_rank"] = 'genus'
            elif animal["taxon_rank"] == 'order':
                animal["taxon_rank"] = 'family'
            elif animal["taxon_rank"] == 'class':
                animal["taxon_rank"] = 'order'

    with open(json_filename, 'w') as outfile:
        json.dump(data, outfile)


def split_num_unit(str):
    match = re.match('([0-9. ]+)([a-z]+)?', str)
    if len(match.groups()) == 0:
        raise Exception('Unable to parse string:'+str)
    if len(match.groups()) == 1:
        return float(match.group(1)), None
    else:
        return float(match.group(1)), match.group(2)

def parse_range_value(value, unit_chars):
    value = value.lower()
    match = re.match('[a-z ]*([0-9].*)', value)
    if not match:
        return (None, None)
    value = match.group(1)
    match = re.match("([0-9.{0} ]+)[-]?([0-9.{0} ]+)?".format(unit_chars), value)
    lengrth = len(match.groups())
    if lengrth < 2:
        raise Exception("Unable to parse length value:"+value)

    unit = None
    if not match.group(2):
        (value, unit) = split_num_unit(match.group(1).strip())
    else:
        (low, unit) = split_num_unit(match.group(1).strip())
        (high, unit) = split_num_unit(match.group(2).strip())
        value = (high + low) / 2

    return value, unit

def getLength(value):
    (value, unit) = parse_range_value(value, 'cm')
    if unit and unit == 'cm':
        value = value / 100
    elif unit and unit == 'mm':
        value = value / 1000
    value = '{:.3f}'.format(value)

    return value


def getHeight(value):
    return getLength(value)


def getLifespan(value):
    (value, unit) = parse_range_value(value, 'daysyears')
    if unit and unit == 'days':
        value = value / 365
    value = '{:.3f}'.format(value)

    return value

def getTopSpeed(value):
    (value, unit) = parse_range_value(value, 'kmph/')
    if (not value):
        return None
    value = '{:.3f}'.format(value)

    return value


def append_list(vals, list):
    for val in vals:
        if not val in list:
            list.append(val)


def append(val, list):
    if not val in list:
        list.append(val)


def crawlAnimalLinks():
    allAnimals = []
    index_page = 'https://a-z-animals.com/animals'
    req = requests.get(index_page)
    tree = html.fromstring(req.content)
    links = tree.xpath('//li/a/@href')
    for i in range(12,len(links)):
        link = "https://a-z-animals.com"+links[i]
        allAnimals.append(link)
    return allAnimals

def process_animal(url):
    req = requests.get(url)
    html_tree = html.fromstring(req.content)
    animal = {}

    try:
        node = html_tree.xpath('//h1/a/@title')
        animal['english_name'] = node[0]
    except:
        print("Name was not retrieved for uri: "+url)
        return None

    node = html_tree.find_class('az-facts')
    if len(node) == 0:
        print("No info table found for url: "+url)
        return None

    taxon_rank = "unknown"
    taxon_name = "unknown"
    scientific_name = "unknown"
    taxonomy = {}
    numerics = {}
    a_eats = []

    node = node[0]
    for row in node.xpath('.//tr'):
        cells = row.xpath('.//td')
        if len(cells) < 2:
            continue
        name = cells[0].xpath('.//b/a')
        if len(name) < 1:
            print ('Name not found in:'+row.text_content())
            continue
        name = name[0].text_content().strip().lower()
        value = cells[1].text_content().strip()
        if name == 'scientific name':
            scientific_name = value
        if name == 'kingdom':
            taxonomy[name] = taxon_name = value
            taxon_rank = name
        elif name == 'phylum':
            taxonomy[name] = taxon_name = value
            taxon_rank = name
        elif name == 'class':
            taxonomy[name] = taxon_name = value
            taxon_rank = name
        elif name == 'order':
            taxonomy[name] = taxon_name = value
            taxon_rank = name
        elif name == 'family':
            taxonomy[name] = taxon_name = value
            taxon_rank = name
        elif name == 'genus':
            taxonomy[name] = taxon_name = value
            taxon_rank = name
        elif name == 'species':
            taxonomy[name] = taxon_name = value
            taxon_rank = name
        elif name == 'group':
            animal['group'] = value
            append(animal['group'], groups)
        elif re.match('other name', name):
            animal['other_names'] = value.replace('and', ',').split(',')
        elif re.match('diet', name):
            animal['diet'] = value.replace(' ', '').split(',')
            append_list(animal['diet'], diets)
        elif re.match('size', name):
            if re.match('(L)', name):
                numerics["length"] = value
            elif re.match('(H)', name):
                numerics['height'] = value
        elif re.match('weight', name):
            numerics['weight'] = value
        elif re.match('top speed', name):
            numerics['top speed'] = value
        elif re.match('lifespan', name):
            numerics['life span'] = value
        elif re.match('conservation', name):
            value = value.lower()
            if not value in conservationCodes.keys():
                print (value+': conservation status not found '+url)
            else:
                animal['conservation'] = conservationCodes[value]

        elif re.match('colour', name):
            animal['color'] = value.split(',')
        elif re.match('food', name) or re.match('prey', name):
            append_list(value.split(','), a_eats)

        elif re.match('predators', name):
            animal['predators'] = value.split(',')
            append_list(animal['predators'],predators)
        elif re.match('habitat', name):
            animal['habitat'] = value.split(',')
            append_list(animal['habitat'], habitats)

    if (taxon_name == "unknown"):
        taxon_name = scientific_name
    if (scientific_name == "unknown"):
        scientific_name = taxon_name

    animal['taxonomy'] = taxonomy
    animal['numerics'] = numerics
    animal['scientific_name'] = scientific_name
    animal['taxon_rank'] = taxon_rank
    animal['taxon_name'] = taxon_name
    animal['eats'] = a_eats
    append_list(a_eats, eats)
    #TODO: biome missing
    #TODO: climate missing

    return animal


def crawlWebsite(animals, start = -1):
    c = 0

    links = crawlAnimalLinks()
    for link in links:
        c += 1
        if c < len(animals) or c < start:
            continue

        animal = {"english_name": "unkown"}
        try:
            animal = process_animal(link)
            if animal:
                animals.append(animal)
        except Exception as e:
            print("Process stopped with an exception for "+link)
            print(str(e))

        if (c % 10 == 0):
            print(c)
            time.sleep(1)
    return animals


def crawl():
    animals = []
    data = {}

    animals = crawlWebsite(animals)
    data["diets"] = diets
    data["habitats"] = habitats
    data["groups"] = groups
    data["eats"] = eats
    data["predators"] = predators
    data["animals"] = animals
    with open(json_filename, 'w') as outfile:
        json.dump(data, outfile)

def crawl_color_eats(from_scratch):
    data = load_data()
    animals = {}
    for animal in data["animals"]:
        name = animal.get("english_name")
        if name and name != 'unknown':
            if not name in animals.keys():
                animals[name] = animal
            else:
                print("repeated animal:"+name)
    if from_scratch:
        crawled = crawlWebsite([])
        with open('data/azanimals_recrawl.txt', 'w') as outfile:
            json.dump(crawled, outfile)

    file = open('data/azanimals_recrawl.txt', 'r')
    crawled = json.load(file)
    print (eats)
    print (predators)
    for animal in crawled:
        name = animal.get("english_name")
        if name and name != 'unknown' and animal.get('color'):
            name = name.lower().replace("genus ", "").strip()
            if animals.get(name):
                animals[name]['color'] = animal['color']
                animals[name]['eats'] = animal['eats']
            else:
                print("taxon_name not found:"+name)
    save_data(data)


if __name__ == "__main__":
    crawl_color_eats(True)
