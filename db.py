"""Handles reading the dictionary of ItemTypes from the XML file.

This is largely copied from the original author's repository, just a bit
stripped down. In particular, this stripped down version requires the XML file
to be topologically sorted.

https://github.com/Omnifarious/factorio_calc/blob/master/factorio_calc.py
"""

import os
import sys
import re
from xml.etree import ElementTree
from fractions import Fraction as _F
from models import ItemType

def _checkXMLHasNoText(xmlel):
    return ((xmlel.text is None) or (xmlel.text.strip() == '')) \
        and ((xmlel.tail is None) or (xmlel.tail.strip() == ''))

class ItemTypeDb(set):
    """A limited dictionary-like structure with all item types.

    Limited means that it does not work exactly like a dictionary. E.g. you
    cannot check for key's existance using "in" statement.
    """

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self._by_name = dict()

    def __getitem__(self, name):
        item = self._by_name.get(name)
        if item is not None:
            return item
        else:
            for item in self:
                if item._name == name:
                    self._by_name[item._name] = item
                    return item
        raise KeyError(name)

    @staticmethod
    def _itemId(item):
        idstr = item._name.lower()
        idstr = re.sub(r'\s+', '_', idstr)
        return idstr

    @staticmethod
    def createFromXML(infile):
        newdb = ItemTypeDb()
        ET = ElementTree
        parser = ET.XMLParser()
        block = infile.read(4 * 1024 * 1024)
        while len(block) > 0:
            parser.feed(block)
            block = infile.read(4 * 1024 * 1024)
        block = None
        tree = parser.close()
        parser = None
        if tree.tag != 'factorio_calc_item_db':
            raise ValueError("Not an XML item database.")
        if tree.attrib.get('version', '1.0') != '1.0':
            raise ValueError(f"Do not know how to handle version "
                             f"{tree.attrib['version']}.")
        if not _checkXMLHasNoText(tree):
            raise ValueError("Invalid XML database.")
        item_idmap = {}
        for itemel in tree.getchildren():
            itemid, item = ItemTypeDb.itemFromXML(item_idmap, itemel)
            item_idmap[itemid] = item
            newdb.add(item)
        return newdb

    @staticmethod
    def itemFromXML(item_idmap, itemel):
        if itemel.tag != 'item':
            raise ValueError(f"Got element '{itemel.tag}', expecting 'item'.")
        itemid = itemel.attrib['id']
        if not _checkXMLHasNoText(itemel):
            raise ValueError(f"Invalid item {itemid}")
        if itemid in item_idmap:
            raise ValueError(f"Item {itemid} defined twice.")
        name = itemel.attrib.get('name', itemid)
        time = itemel.attrib.get('time', None)
        produced = itemel.attrib.get('produced', None)
        if (produced is None) != (time is None):
            raise ValueError(f"Invalid item '{itemid}'.")
        if time is not None:
            time = _F(time)
            produced = int(produced)
        ingredients = []
        for ingredientel in itemel.getchildren():
            if ingredientel.tag != 'ingredient':
                raise ValueError(f"Item {itemid} has {ingredientel.tag}")
            ingid = ingredientel.attrib['idref']
            if not _checkXMLHasNoText(ingredientel):
                raise ValueError(f"Invalid ingredient '{ingid}' in '{itemid}'")
            ingcount = int(ingredientel.attrib['count'])
            if ingid not in item_idmap:
                raise ValueError(f"Item '{itemid}' mentions ingredient "
                                 f"'{ingid}' before it's defined.")
            ingredients.append((ingcount, item_idmap[ingid]))
        if (len(ingredients) > 0) and (time is None):
            raise ValueError(f"Item '{itemid}' has ingredients but "
                             "no production time.")
        return (itemid,
                ItemType(name, time, tuple(ingredients), produced))

def load():
    dbdir = os.path.dirname(__file__)
    xml_fname = os.path.join(dbdir, 'items.xml')

    if os.path.exists(xml_fname):
        with open(xml_fname, 'r') as _item_f:
            item_db = ItemTypeDb.createFromXML(_item_f)
    else:
        raise Exception("No items.xml found")

    return item_db
