import sys
import argparse
from fractions import Fraction as _F

import db
from models import ItemTypeDemand, DemandGraph

parser = argparse.ArgumentParser(
    description='Generate a graphviz dot graph for Factorio demands.'
)
parser.add_argument(
    'demands',
    type=str, 
    help='Expression, e.g. "2*Inserter + 1/2 * Black Science"'
)
parser.add_argument(
    '--bus',
    type=str,
    default='',
    help='Coma-separated list of "unlimited" stuff on your bus, e.g. "Iron Plate, Engine"'
)

args = parser.parse_args()
item_types = db.load()

def _parse_section(section):
    try:
        try:
            num, name = section.split("*")
        except:
            num, name = section.strip().split(" ", 1)
        num = _F(num)
        name = name.strip()
    except:
        raise Exception("Expecting the format similar to: "
                        "\"2*Inserter + 1/2 * Black Science\"")
    return num, _parse_item_type(name)

def _parse_item_type(name):
    try:
        item_type = item_types[name]
    except:
        raise Exception("Could not find %s in XML file" % (name,))
    return item_type

if __name__ == "__main__":
    graph = DemandGraph()
    bus_items = [x.strip() for x in args.bus.split(",") if len(x.strip()) > 0]
    for bus_item in bus_items:
        item_type = _parse_item_type(bus_item)
        graph.add_new_provided(item_type)
    sections = args.demands.split("+")
    for section in sections:
        num, item_type = _parse_section(section)
        graph.add_new_demand(ItemTypeDemand(item_type, num), explicit=True)
    print(graph.generate_dot_graph())
