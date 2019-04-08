import sys
from fractions import Fraction as _F

import db
from models import ItemTypeDemand, DemandGraph

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
    try:
        item_type = item_types[name]
    except:
        raise Exception("Could not find %s in XML file" % (item_name,))
    return num, item_type

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise Exception("Expecting \"exactly one argument\".")
    the_arg = sys.argv[1]
    graph = DemandGraph()
    sections = the_arg.split("+")
    for section in sections:
        num, item_type = _parse_section(section)
        graph.add_new_demand(ItemTypeDemand(item_type, num))
    print(graph.generate_dot_graph())
