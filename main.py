import animaliaBio
import azanimals
from owlready2 import *
import json
import requests
from lxml import html
import re
import time

base_uri = "http://www.semanticweb.org/sara/ontologies/VertebrateTaxonomy#"
ontologyPath = "data/VertebratesTaxonomy.owl"
outputPath = "data/VertebratesTaxonomy_populated.owl"

animaliaBioFile = "data/animalia_bio.txt"
merged_data_file = "data/merged_data.txt"


mammalClass = 'mammalia'
birdsClass = 'aves'
reptileClass = 'reptilia'
amphibianClass = 'amphibia'
marsupialOrders = ["didelphimorphia",
                   "paucituberculata",
                   "microbiotheria",
                   "yalkaparidontia",
                   "dasyuromorphia",
                   "notoryctemorphia",
                   "peramelemorphia",
                   "diprotodontia"]
monotremeOrder = "monotremata"

fishClasses = ["myxini"
"pteraspidomorphi",
"thelodonti",
"anaspida",
"petromyzontida",
"hyperoartia",
"conodonta",
"cephalaspidomorphi",
"placodermi",
"chondrichthyes",
"acanthodii",
"actinopterygii",
"sarcopterygii"
]

diets = ["Herbivore", "Carnivore", "Omnivore"]
habitats = ["Terrestrial", "Aquatic"]
climates = []

scalar_keys = ["conservation", "diet"]
list_keys = ["other_names", "eats", "predators" "biome", "climate", "habitat", "color"]
numeric_keys = ['life span', 'top speed', 'length', "height"]

def populate_animal(animal, owl_class, onto):
    try:
        individual = animal.get("english_name").title().replace(' ','')
        instance = owl_class(individual)
    except:
        print ("Skip animal due to error in name:" + animal.get("english_name"))
        return

    instance.hasEnglishName.append(animal.get("english_name").title())
    #instance.hasTaxonName = animal["taxon_name"].title()
    if animal.get("persian_name"):
        instance.hasPersianName.append(animal["persian_name"])
    #else:
    #    print("no persinan name for: " + animal["english_name"])
    if animal.get("other_names"):
        for name in animal["other_names"]:
            instance.hasEnglishName.append(name.title())
    if animal.get("color"):
        for name in animal["color"]:
            instance.hasColor.append(name.title())

    if (animal["taxon_rank"] == "class"):
        animal["taxon_rank"] = "classe"

    instance.hasTaxonomicRank = onto.search(iri='*#{}'.format(animal.get("taxon_rank").capitalize()))[0]
    taxonomy = animal.get("taxonomy")
    if taxonomy.get("kingdom"):
        instance.hasKingdomName =  taxonomy.get("kingdom").title()
    if taxonomy.get("phylum"):
        instance.hasPhylumName = taxonomy.get("phylum").title()
    if taxonomy.get("class"):
        instance.hasClassName = taxonomy.get("class").title()
    if taxonomy.get("order"):
        instance.hasOrderName = taxonomy.get("order").title()
    if taxonomy.get("family"):
        instance.hasFamilyName = taxonomy.get("family").title()
    if taxonomy.get("genus"):
        instance.hasGenusName = taxonomy.get("genus").title()
    if taxonomy.get("species"):
        instance.hasSpeciesName = taxonomy.get("species").title()



    #TODO: extinctIn

    numberics = animal.get("numerics")
    if numberics.get("length"):
        instance.hasAverageBodyLength = float(numberics.get("length"))
    if numberics.get("height"):
        instance.hasAverageHeight = float(numberics.get("height"))
    if numberics.get("life span"):
        instance.hasAverageLifespan = float(numberics.get("life span"))
    if numberics.get("top speed"):
        instance.hasTopSpeed = float(numberics.get("top speed"))

    if animal.get("conservation"):
        instance.hasConservationStatus = onto.search(iri='*#{}'.format(animal.get("conservation")))[0]

    #todo: extend diet list
    if animal.get("diet"):
        instance.hasDiet = onto.search(iri='*#{}'.format(animal["diet"]))[0]

    for habitat in (animal.get("habitat") or []):
        instance.hasHabitat.append(onto.search(iri='*#{}'.format(habitat))[0])

    for cliamte in animal.get("climate") or []:
        instance.livesInClimate.append(onto.search(iri='*#{}'.format(cliamte.replace('/', '-')))[0])



def populate_ontology():
    onto = get_ontology(ontologyPath)
    onto.load()

    animals = load_data()
    for animal in animals:
        if not animal.get("taxon_name"):
            continue
        owl_class = None
        if not animal.get("taxonomy").get("class"):
            continue
        if animal.get("taxonomy")["class"] == birdsClass:
            owl_class = onto.Bird
        elif animal.get("taxonomy")["class"] == reptileClass:
            owl_class = onto.Reptile
        elif animal.get("taxonomy")["class"] == amphibianClass:
            owl_class = onto.Amphibian
        elif animal.get("taxonomy")["class"] == mammalClass:
            owl_class = onto.Placental
            if animal.get("taxonomy")["order"] == monotremeOrder:
                owl_class = onto.Monotreme
            elif  animal.get("taxonomy")["order"] in marsupialOrders:
                owl_class = onto.Marsupial
        elif animal.get("taxonomy")["class"] in fishClasses:
            owl_class = onto.Fish
            animal["habitat"] = ["Aquatic"]
        if (not owl_class):
            print("Non verteberate animal skipped:" + animal["english_name"])
            print(animal.get("taxonomy"))
            continue

        populate_animal(animal, owl_class, onto)

    onto.save(outputPath)


def compare_two_datasets():
    animalia_data = animaliaBio.load_data()
    azanimal_data = azanimals.load_data()

    same_traxon = 0
    for animal1 in animalia_data["animals"]:
        for animal2 in azanimal_data["animals"]:
            if ('taxon_name' in animal1.keys() and 'taxon_name' in animal2.keys() ):
                if animal1["taxon_name"] == animal2["taxon_name"] and animal1["taxon_rank"] != animal2["taxon_rank"]:
                    print("same taxon_name different taxon_rank: {0}({1}) {2}({3})".format(animal1["english_name"], animal1["taxon_rank"], animal2["english_name"], animal2["taxon_rank"]))
                    animal2["taxon_name"] = animal1["taxonomy"][animal2["taxon_rank"]]
                if animal1["taxon_name"] == animal2["taxon_name"] and animal1["english_name"] != animal2["english_name"]:
                    if animal1["english_name"] in animal2["other_names"]:
                        animal1["english_name"] = animal2["english_name"]
                    else:
                        print("same taxon_name different english_name: {0}({1}) {2}({3}) >> {4}".format(animal1["english_name"], animal1["taxon_rank"], animal2["english_name"], animal2["taxon_rank"],animal1["taxon_name"]))
                        animal2["other_names"].append(animal1["english_name"])
                if animal1["taxon_name"] != animal2["taxon_name"] and animal1["english_name"] == animal2["english_name"]:
                    print("same english name different taxon_name: {0}({1}) {2}({3})".format(animal1["english_name"], animal1["taxon_name"], animal2["english_name"], animal2["taxon_name"]))
                    animal2["taxon_name"] = animal2["taxonomy"]["species"] = animal2["scientific_name"] = animal1["taxon_name"]
                if animal1["taxon_name"] == animal2["taxon_name"]:
                    same_traxon += 1
    #azanimals.save_data(azanimal_data)
    #animaliaBio.save_data(animalia_data)
    print("The same animnals:{0}".format(same_traxon))


def getPersianName(taxon_name):
    try:
        link = "https://en.wikipedia.org/wiki/"+taxon_name.replace(' ', '_')
        req = requests.get(link)
        tree = html.fromstring(req.content)
        title = tree.xpath('//li[@class="interlanguage-link interwiki-fa"]/a/@title')
        if len(title):
            return title[0].split('–')[0].strip()
    except:
        print("persian name not found for " + taxon_name)
        return None


def getPersianNames():
    data_set = (animaliaBio.load_data(), azanimals.load_data())
    counter = 0
    for data in data_set:
        for animal in data["animals"]:
            name = animal.get("taxon_name")
            if name:
                persian_name = getPersianName(name)
                if persian_name:
                   animal["persian_name"] = persian_name
            counter += 1
            if (counter % 10) == 0:
                time.sleep(1)
                print(counter)

    animaliaBio.save_data(data_set[0])
    azanimals.save_data(data_set[1])


def merge_animals(animal1, animal2):
    for key in scalar_keys:
        value = animal1.get(key)
        if not value or value == 'unknown':
            if animal2.get(key):
                animal1[key] = animal2[key]
    for key in list_keys:
        if not animal1.get(key):
            animal1[key] = []
        if animal2.get(key):
            for value in animal2[key]:
                animal1[key].append(value)
    for key in numeric_keys:
        if not animal1.get('numerics'):
            animal1['numerics'] = {}
        if not animal1['numerics'].get(key) and animal2.get('numerics') and animal2['numerics'].get(key):
            animal1['numerics'][key] = animal2['numerics'].get(key)


def merge_datasets():
    data_set = (animaliaBio.load_data(), azanimals.load_data())
    counter = 0
    animals = {}   # list of all animals
    for data in data_set:
        for animal in data["animals"]:
            if animal.get('color'):  #remove habitat from a-zanimal entities
                animal.pop('habitat', None)

            name = animal.get("english_name")
            if not name:
                continue
            climate = []
            if animal.get('climate'):  # remove repeated climates
                azanimals.append_list(animal["climate"], climate)
            animal["climate"] = climate

            rank = animal.get("taxon_rank")
            taxon = animal["taxonomy"].get(rank)
            if rank and rank != 'unknown' and (not taxon or (taxon != animal['taxon_name'])) :
                animal["taxonomy"][rank] = animal['taxon_name']

            if animals.get(name):
                merge_animals(animals.get(name), animal)
            else:
                animals[name] = animal

    with open(merged_data_file, 'w', encoding='utf-8') as outfile:
        data = []
        for animal in animals.values():
            data.append(animal)
        json.dump(data, outfile)

def load_data():
    file = open(merged_data_file)
    data = json.load(file)
    return data

def save_data(data):
    with open(merged_data_file, 'w') as outfile:
        json.dump(data, outfile)

def process_eats():
    data = load_data()

    az = azanimals.load_data()
    foods = []
    for animal in az["animals"]:
        if animal.get('eats'):
            azanimals.append_list(animal["eats"], foods)
        #if animal.get('predators'):
        #    azanimals.append_list(animal["predators"], foods)

    for food in foods:
        if data.get(food.lower()):
            print ("food found: "+food)
            continue
        match = re.match('(.*)s$', food)
        if match:
            single = match.group(1)
            if data.get(single.lower()):
                print("food found after singularification:"+single)
                continue
        print("food not found:"+food)


animaliaBio.fix_numeric_data()
azanimals.fix_numeric_data()
animaliaBio.fix_habitat()
animaliaBio.fix_taxon_case()
azanimals.fix_taxon_case()
animaliaBio.fix_names()
azanimals.fix_names()
azanimals.fix_genus_taxon()
animaliaBio.fix_genus()
azanimals.fix_genus()
azanimals.fix_diet()

compare_two_datasets()

getPersianNames()
#process_eats()

#merge_datasets()
populate_ontology()