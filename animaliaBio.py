import requests
from lxml import html
import re
import time
import json
import os.path


json_filename = 'data/animalia_bio.txt'

def makeLink(animalCategory, pageNumber, url='http://animalia.bio'):
    return url + '/' + animalCategory + '/?page=' + str(pageNumber)


animalCategories = [ {"name": "reptiles", "pages": 1}, {"name": "mammals", "pages": 19}, {"name": "birds", "pages": 5}]
conservationCodes = { "ne": "NotEvaluated", "dd":"DataDeficient",  "lc":"LeastConcern", "nt":"NearThreatened", "cd":"ConservationDependent",
                      "vu":"Vulnerable", "en":"Endangered", "cr":"CriticallyEndangered", "ew":"ExtinctInTheWild", "ex":"CompletelyExtinct" }
herbivores = ["Herbivore", "Frugivore", "Folivore", "Granivore", "Graminivore", "Nectarivore", "Nectarivore", "Gumivorous", "Palynivore" ]
carnivores = ["Carnivore", "Insectivores", "Vermivorous", "Scavenger", "Predator", "Mesopredator", "Hypercarnivore","Piscivores"]


climates = []
lifestyles = []
diets = []
biomes = []
animals = []


def load_data():
    file = open(json_filename)
    data = json.load(file)
    return data

def save_data(data):
    with open(json_filename, 'w') as outfile:
        json.dump(data, outfile)

def fix_names():
    file = open(json_filename)
    data = json.load(file)
    for animal in data["animals"]:
        animal["english_name"] = animal["english_name"].lower().strip()

    with open(json_filename, 'w') as outfile:
        json.dump(data, outfile)

def fix_genus():
    file = open(json_filename)
    data = json.load(file)
    for animal in data["animals"]:
        if 'taxon_name' in animal.keys() and re.match('genus ', animal["taxon_name"]):
            animal["taxon_name"] = animal["taxonomy"]["genus"]
            animal["taxon_rank"] = 'genus'
            animal['taxonomy'].pop('species', None)

    with open(json_filename, 'w') as outfile:
        json.dump(data, outfile)

def fix_taxon_case():
    file = open(json_filename)
    data = json.load(file)
    for animal in data["animals"]:
        for key in animal["taxonomy"]:
            animal["taxonomy"][key] = animal["taxonomy"][key].lower().strip().replace('_', ' ')
        if 'taxon_name' in animal.keys():
            animal["taxon_name"] = animal["taxon_name"].lower().strip().replace('_', ' ')

    with open(json_filename, 'w') as outfile:
        json.dump(data, outfile)

def fix_habitat():
    animalbio = open(json_filename)
    data = json.load(animalbio)
    for animal in data["animals"]:
        isTrs = False
        isAqua = False
        if len(set(animal["lifestyle"]).intersection(set(["Terrestrial", "Arboreal", "Fossorial"]))) > 0:
            isTrs = True
        if "Aquatic" in animal["lifestyle"]:
            isAqua = True
        if "Semiaquatic" in animal["lifestyle"]:
            isTrs = True
            isAqua = True
        animal["habitat"] = []
        if isTrs:
            animal["habitat"].append("Terrestrial")
        if isAqua:
            animal["habitat"].append("Aquatic")

        if len(animal["habitat"]) == 0:
            if ('taxon_rank' in animal.keys()):
                if re.match('sea', animal["english_name"].lower()):
                    animal["habitat"].append("Aquatic")
                else:
                    animal["habitat"].append("Terrestrial")
            else:
                print("no hatiat for "+animal["english_name"])

    with open(json_filename, 'w') as outfile:
        json.dump(data, outfile)

def fix_numeric_data():
    animalbio = open(json_filename)
    data = json.load(animalbio)
    for animal in data["animals"]:
        print(animal["english_name"])
        if "length" in animal["numerics"].keys():
            animal["numerics"]["length"] = getLength(animal["numerics"]["length"])
        if "height" in animal["numerics"].keys():
            animal["numerics"]["height"] = getHeight(animal["numerics"]["height"])
        if "life span" in animal["numerics"].keys():
            animal["numerics"]["life span"] = getLifespan(animal["numerics"]["life span"])
        if "top speed" in animal["numerics"].keys():
            animal["numerics"]["top speed"] = getTopSpeed(animal["numerics"]["top speed"])

    with open(json_filename, 'w') as outfile:
        json.dump(data, outfile)


def fix_diet():
    animalbio = open(json_filename)
    data = json.load(animalbio)

    for animal in data["animals"]:
        isHerbi = isCarni = isOmni = False
        if isinstance(animal["diet"], str):
            continue

        for diet in animal["diet"]:
            if diet in carnivores:
                isCarni = True
            if diet in herbivores:
                isHerbi = True
            if diet == 'Omnivore':
                isOmni = True

        if isOmni or (isHerbi and isCarni):
            animal["diet"] = "Omnivore"
        elif isCarni:
            animal["diet"] = "Carnivore"
        elif isHerbi:
            animal["diet"] = "Herbivore"
        else:
            animal.pop('diet', None)
            print("No diet for {0}".format(animal["english_name"]))


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
    value = '{:.3f}'.format(value)
    return value

def crawlAnimalLinks(animalType, animalTypePages):
    allAnimals = []
    for i in range(animalTypePages):
        req = requests.get(makeLink(animalCategory=animalType, pageNumber=i))
        tree = html.fromstring(req.content)
        links = tree.xpath('//a[@class="item-animal rounded"]/@href')
        for i in range(len(links)):
            allAnimals.append(links[i])
    return allAnimals

def process_animal(url):
    req = requests.get(url)
    html_tree = html.fromstring(req.content)
    animal = {}

    try:
        node = html_tree.find_class('s-char-heading')
        animal['english_name'] = node[0].find_class('a-h1')[0].text_content().strip()
    except:
        print (url)
        name = re.search('.*/(.*)$', url).group(1).replace('_', ' ').replace('-', ' ')
        name = ''.join([name[0].upper(), name[1:].lower()])
        animal['english_name'] = name
        print("Name retrieved from uri: "+name)

    taxon_rank = taxon_name = None
    taxonony = {}
    for node in html_tree.find_class('s-char-kinds__item'):
        taxon_rank = node.find_class('s-char-kinds__attr')[0].text_content().strip()
        taxon_rank  = ''.join([taxon_rank[0].upper(), taxon_rank[1:].lower()])
        taxon_name = node.find_class('s-char-kinds__name')[0].text_content().strip()
        taxonony[taxon_rank] = taxon_name
    if taxon_name:
        animal['taxon_rank'] = taxon_rank
        animal['taxon_name'] = "_".join(taxon_name.lower().split(' '))
    else:
        print("No taxon name for "+animal["english_name"])
    animal['taxonomy'] = taxonony

    numerics = {} #lifespan, length, height
    for node in html_tree.find_class('s-char-char__wrap'):
        a = node.find_class('s-char-char__name')
        try:
            name = node.find_class('s-char-char__name')[0].text_content().strip()
            value = node.find_class('s-char-char__num')[0].text_content().strip()
            numerics[name.lower()] = value
        except:
            print("Numberic data failure for "+ animal["english_name"])

    animal['numerics'] = numerics

    traits = []  #Herbivore, Terrestrial,
    for node in html_tree.find_class('s-char-status-item'):
        try:
            traits.append(node.xpath('@title')[0].strip())
        except:
            print("Traits data failure for " + animal["english_name"])
    animal['traits'] = traits

    biome = []
    try:
        for node in html_tree.find_class('s-distr-zone')[0].find_class('s-distr-margin'):
            text = node.text_content().strip()
            biome.append(text)
            if not (text in biomes):
                biomes.append(text)
    except:
        print("Biome data failure for " + animal["english_name"])
    animal['biome'] = biome


    climate = []
    try:
        for node in html_tree.find_class('s-distr-climate')[0].find_class('s-distr-margin'):
            text = node.text_content().strip()
            climate.append(text)
            if not (text in climates):
                climates.append(text)
    except:
        print("Climate data failure for " + animal["english_name"])
    animal['climate'] = climate

    lifestyle = []
    for node in html_tree.find_class('s-habbit-group'):
        try:
            name = node.find_class('s-habbit-group__slug')[0].text_content().strip()
        except:
            print("Lifestyle data failure for " + animal["english_name"])
        if name != 'Lifestyle':
            continue
        for title in node.xpath('//a/@title'):
            lifestyle.append(title)
            if not (title in lifestyles):
                lifestyles.append(title)
    animal['lifestyle'] = lifestyle

    diet = []
    for node in html_tree.find_class('s-diet-item__link'):
        text = node.text_content().strip()
        diet.append(text)
        if not (text in diets):
            diets.append(text)
    animal['diet'] = diet

    conservation = "ne"
    for node in html_tree.find_class('s-population-view__item'):
        if 'active' in node.classes:
            conservation = node.text_content().strip().lower()
    animal['conservation'] = conservationCodes[conservation]


    return animal


def crawlWebsite(animals, start = -1):
    c = 0

    for animalCategory in animalCategories:
        print(animalCategory["name"])
        links = crawlAnimalLinks(animalCategory["name"], animalCategory["pages"])
        for link in links:
            c += 1
            if c < len(animals) or c < start:
                continue
            time.sleep(1)
            animal = {"english_name": "unkown"}
            try:
                animal = process_animal(link)
                animals.append(animal)
            except Exception as e:
                print("Process stopped on animal {} no {} with an exception".format(animal.get("english_name"),c))
                print(str(e))

            if (c % 10 == 0):
                print(c)
    return animals


if __name__ == "__main__":
    animals = []
    data = {}
    if os.path.exists(json_filename):
        infile = open(json_filename, 'r')
        data = json.load(infile)
        animals = data["animals"]
        climates = data["climates"]
        lifestyles = data["lifestyles"]
        diets = data["diets"]
        biomes = data["biomes"]

    animals = crawlWebsite(animals)
    data["climates"] = climates
    data["lifestyles"] = lifestyles
    data["diets"] = diets
    data["biomes"] = biomes
    data["animals"] = animals
    with open(json_filename, 'w') as outfile:
        json.dump(data, outfile)




