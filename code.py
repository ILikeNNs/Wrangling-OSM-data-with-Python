"""
Created on Tue Jul 12 23:00:24 2016

@author: Lukasz
"""
#!/usr/bin/env python
#-*- coding: utf-8 -*-
import xml.etree.cElementTree as ET
import operator
import re
import codecs
import json

problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

CREATED = ['version', 'changeset', 'timestamp', 'user', 'uid']


def shape_element(element):
    node = {}
    if element.tag == 'node' or element.tag == 'way':
        node['type'] = element.tag
        #defining a list for GPS coordinates
        pos = [0,0]
        for every in element.keys():
            #checking if the current key is in CREATED list
            #if it is, we create or edit the dictionary element
            if every in CREATED:
                if 'created' not in node.keys():
                    node['created'] = {}
                    node['created'][every] = element.get(every)
                else:
                    node['created'][every] = element.get(every)
            #building coordinates and ensuring float values
            elif every in ['lat', 'lon']:
                if every == 'lat':
                    pos[0] = float(element.get(every))
                elif every == 'lon':
                    pos[1] = float(element.get(every))
                node['pos'] = pos
            else:
                node[every] = element.get(every)
            for elem in element.iter('tag'):
                elemkey = elem.attrib['k']
                elemval = elem.attrib['v']
                #if we find problematic chars, we go to the next element of the loop
                if problemchars.search(elemkey):
                    continue
                else:
                    #taking care of tags with "addr" fragment
                    if elemkey.count(":") == 1:        
                        if elemkey.startswith("addr:"):
                            if 'address' not in node.keys():
                                node['address'] = {}
                                node['address'][elemkey[5:]] = elemval
                            else:
                                node['address'][elemkey[5:]] = elemval
                    elif elemkey.count(":") > 1:
                        continue
                    elif elemkey.count(":") < 1:
                        node[elemkey] = elemval
        #building a node refs list
        for each in element.iter("nd"):
            if "node_refs" not in node.keys():
                node["node_refs"] = []
            node["node_refs"].append(each.attrib["ref"])
        #filter elements included in .json
        #for some reason the iterator does include types other than "way"
        #and "node". The following lines help to overcome the problem
        if node["type"] in ["way", "node"]:    
            return node
        else:
            return None
    else:
        return None

#the compiled list of names after auditing the data
#for elements that appear most frequently
unicodeDelString = re.compile(u'J\xf3zefa|Tadeusza|Juliusza|Walerego|Jana|Henryka|Stanis\u0142awa|Ksi\u0119dza|Kazimierza|Jerzego|Samuela|Marsza\u0142ka|Adama|Zygmunta|Ignacego|Pu\u0142kownika|W\u0142adys\u0142awa|Franciszka|Ferdynanda|Genera\u0142a|Antoniego|i|Heleny|Leona|J\u0119drzeja')     
unicodeNoNDelString = re.compile(u'Kr\xf3lowej Jadwigi|Kazimierza Wielkiego|Aleja Jana Paw\u0142a II')

#the following procedure helps to change the names of the streets
def change_name(el):
    #checking if we do not get a KeyError
    try:
        if unicodeNoNDelString.search(el["address"]["street"]):
            pass
        else:
            name = el["address"]["street"].split(" ")
            #if the name contains one word, it cannot contain a first name
            if len(name) <= 1:
                pass
            else:
                for i in name:
                    #if we find one of the names we would like to change
                    #we remove the element with the first name
                    if unicodeDelString.search(i):
                        name.pop(name.index(i))
        #we join the remaining elements and return the correct name
            el["address"]["street"] = ' '.join(name)
        return el
    except KeyError:
        pass


#the following procedure helps to establish which elements should be changed;
#in other words, how the predefined list of names needs to be built
#the procedure builds dictionaries of streets with two, three or more words in it
#then it builds lists of tuples sorted in descending order
def counter(filename):
    streets2 = {}
    streets3 = {}
    streetsmore = {}
    for event, element in ET.iterparse(filename, events=("start",)):
        if element.tag == "way" or element.tag == "node":
            for tag in element.iter("tag"):
                try:
                    if tag.attrib["k"] == "addr:street":
                        name = tag.attrib["v"].split(" ")
                        if len(name) == 2:
                            if tag.attrib["v"] not in streets2.keys():
                                streets2[tag.attrib["v"]] = 1
                            else:
                                streets2[tag.attrib["v"]] += 1
                        elif len(name) == 3:
                            if tag.attrib["v"] not in streets3.keys():
                                streets3[tag.attrib["v"]] = 1
                            else:
                                streets3[tag.attrib["v"]] += 1
                        elif len(name) > 3:
                            if tag.attrib["v"] not in streetsmore.keys():
                                streetsmore[tag.attrib["v"]] = 1
                            else:
                                streetsmore[tag.attrib["v"]] += 1
                except KeyError:
                    continue
    #the fragment that deals with sorting and converting into a list
    two = sorted(streets2.items(), key=operator.itemgetter(1), reverse=True)
    three = sorted(streets3.items(), key=operator.itemgetter(1), reverse=True)
    more = sorted(streetsmore.items(), key=operator.itemgetter(1), reverse=True)
    joinlist = [i[0] for i in two[:10]] + [i[0] for i in three[:10]] + [i[0] for i in more[:10]]
    #unblock a below line if want to see list of tuples
    #print two[:10], three[:10], more[:10]
    #block a below line if want to see list of tuples and not a combined list of all street names
    return joinlist

elem = counter('krakow2.osm')
#unblock a below line if you want to see the list
#print elem

#writing function taken out of process_map to make it shorter
def printing(infile,element,pretty=False):
    if pretty:
        infile.write(json.dumps(element, indent=2, ensure_ascii=False)+"\n")
    else:
        infile.write(json.dumps(element, ensure_ascii=False) + "\n")
    
def process_map(file_in):
    #it was changed to process each element's name, whenever necessary
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w", encoding='utf-8') as fo:
        #I only take 10 most frequent elements from all street names
        lista = counter("krakow2.osm")
        for _, element in ET.iterparse(file_in):
            el = shape_element(element)
            if el:
                try:
                    #checking if the street name is on the list of most frequent names
                    if el["address"]["street"] in lista:
                        #if it is a royal name (or the Pope), just append
                        if unicodeNoNDelString.search(el["address"]["street"]):
                            data.append(el)
                            printing(fo,el,pretty=False)
                        #if it is a first name, a military or religious title, change name
                        elif unicodeDelString.search(el["address"]["street"]) and not unicodeNoNDelString.search(el["address"]["street"]):
                            change_name(el)
                            data.append(el)
                            printing(fo,el,pretty=False)
                        #for other possible cases
                        else:
                            data.append(el)
                            printing(fo,el,pretty=False)
                    #if the name is not on the list, append as is
                    else:
                        data.append(el)
                        printing(fo,el,pretty=False)
                #if there is no such key, append as is
                except KeyError:
                    data.append(el)
                    printing(fo,el,pretty=False)
    return data

process_map("krakow2.osm")  
 