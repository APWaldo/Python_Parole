import csv
import requests
import mechanize
import bs4
import json
import sys

parole_data = csv.DictReader(open("scrape.csv"))
persons = [person for person in parole_data]


def get_inmate(nysid_number,nysid_letter):
    br = mechanize.Browser()
    br.set_handle_robots(False)
    #The url I am trying to work with.
    url = 'http://nysdoccslookup.doccs.ny.gov/'

    #Just reading the text on the page.
    response = br.open(url)
    br.select_form(nr=2)
    
    #Setting the values for control fields(username and password)
    for control in br.form.controls:
        if control.name == "M00_NYSID_FLD1I":
            br[control.name] = nysid_number
        if control.name == "M00_NYSID_FLD2I":
            br[control.name] = nysid_letter

    #submitting the form
    results = br.submit().read()
    
    return {"result": results, "br": br}

def is_multiple_crimes(soup): 
    return soup.find('h2').text.startswith("Commitment History") 

def scrape(start, to):
    all_results = []
    for num, person in enumerate(persons[start:to]):
        if num % 10 == 0:
            print >>sys.stderr, num, person
        result = get_inmate(person["nysid1"], person["nysid2"])
        all_results.append((result, person))
    return all_results

def scrape_multiple_crimes(page):
    page_text = page["result"]
    br = page["br"]
    n_forms = get_number_offense(page_text)
    output = []
    for i in range(n_forms):
        br.select_form(nr=i+2)
        single_offense_text = br.submit().read()
        output.append(bs4.BeautifulSoup(single_offense_text))
        br.back()
    return output
        

def get_number_offense(text):
    counter = 0
    soup = bs4.BeautifulSoup(text)
    for link in soup.select(".buttolink"):
        if link.attrs['value'] != '':
            counter = counter + 1
    return counter





def remove_spurious_space(s):
    return str.join(" ", s.strip().split())

def convert_soup_to_crime(soup):
    output = {"identifying": {}, "crimes": [], "sentence" : {} }
    identifying, crimes, sentence = soup.find_all("table")
    for row in identifying.select("tr"):
        a = row.find('a')
        if a is None:
            key = row.find("th").text.strip()
        else:
            key = remove_spurious_space(a.attrs["title"])
        value = row.find("td").text.strip()
        output["identifying"][key] = value

    for row in crimes.select("tr"):
        crime = {}
        for col in row.select("td"):
            key = col.attrs["headers"][0]
            value = remove_spurious_space(col.text)
            if value != "":
                crime[key] = value
        if len(crime) != 0:
            output["crimes"].append(crime)

    for row in sentence.select("tr"):
        a = row.find('a')
        key = remove_spurious_space(a.attrs["title"])
        value = remove_spurious_space(row.find("td").text)
        output["sentence"][key] = value
    return output
    
def make_new_inmate():
    return { "nysid": None, "offenses": [] }

def main():
    full_set = []
    
    if len(sys.argv) == 3:
        start = int(sys.argv[1])
        to = int(sys.argv[2])
    else:
        start = 0
        to = len(persons)
    
    data_set = scrape(start, to)    
    for i, data in enumerate(data_set):
        #import pdb; pdb.set_trace()
        page_data, person = data
        inmate = make_new_inmate()
        soup = bs4.BeautifulSoup(page_data["result"])
        if is_multiple_crimes(soup):
            multi_crime_data = scrape_multiple_crimes(page_data)
            for soup in multi_crime_data:
                one_crime = convert_soup_to_crime(soup)
                inmate["offenses"].append(one_crime)

        else:
            inmate["offenses"].append(convert_soup_to_crime(soup))
        inmate["nysid"] = person["NYSID"]
        full_set.append(inmate)
    
    print json.dumps(full_set, indent=2)

if __name__ == "__main__":
    main()
