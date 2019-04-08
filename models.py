"""This handles all data types and relationships between them.

A bit similar to ProductionItem and ItemSet classes in the original, but mostly
rewritten. I focused on different functionalities then the origianal.
https://github.com/Omnifarious/factorio_calc/blob/master/factorio_calc.py
"""

from fractions import Fraction as _F

class ItemType:
    """Describes a single type of item (e.g. an inserter).

    In particular, it also describes what you need in order to produce it.
    """

    def __init__(self, name, time, ingredients, produced):
        assert isinstance(name, str)
        self._name = name
        # How many items are produced in how much time, by 1.0 factory?
        assert isinstance(produced, int) or produced is None, \
            "expected int or None, got %s" % type(produced)
        self._produced = produced
        assert isinstance(time, _F) or time is None, \
            "expected Fraction or None, got %s" % type(produced)
        self._time = time
        # How many ingredients of which type is needed to produce this amount?
        for count, ingr_type in ingredients:
            #assert isinstance(ingr, SingleIngredientRequirements)
            assert isinstance(count, int), \
                "expected int, got %s" % type(count)
            assert isinstance(ingr_type, ItemType), \
                "expected ItemType, got %s" % type(ingr_type)
        self._ingredients = ingredients

    def __repr__(self):
        return f'ItemType({self._name!r}, {self._time}, ' \
            f'{self._ingredients!r}, produced={self._produced})'

    def __str__(self):
        return self._name

    @property
    def rate_of_one_factory(self):
        """How many items can be produced per second, by one factory?

        Fraction or None. None is returned if (according to the XML) the item is
        "raw" and as such cannot be supplied by any factory.
        """
        if self._produced is None:
            return None
        else:
            base_rate = (self._produced / _F(1,1)) / (self._time / _F(1,1))
            return base_rate

    def ingredient_demand_of_one_factory(self):
        """What's the demand on ingredients needed to keep one factory running?

        Either list of ItemTypeDemand objects, or None. None is returned if
        (according to the XML) the item is "raw" and as such cannot be supplied
        by any factory.
        """
        if self._produced is None:
            return None
        result = []
        for count, ingr_type in self._ingredients:
            result.append(ItemTypeDemand(ingr_type, _F(count, self._time)))
        return result

    def factories_needed_for(self, rate):
        """How many factories are needed to produce `rate` items per second?

        Fraction or None. None is returned if (according to the XML) the item is
        "raw" and cannot be supplied by any factory.
        """
        if self._produced is None:
            return None
        else:
            return rate / self.rate_of_one_factory

    def ingredient_demand_needed_for(self, rate):
        """What's the demand on ingredients needed to produce a given rate?

        rate = items per second.

        Either list of ItemTypeDemand objects, or None. None is returned if
        (according to the XML) the item is "raw" and cannot be supplied by any
        factory.
        """
        multipler = self.factories_needed_for(rate)
        if multipler is None:
            return None
        result = []
        for d in self.ingredient_demand_of_one_factory():
            result.append(ItemTypeDemand(
                d.item_type, d.requested_rate * multipler
            ))
        return result

class ItemTypeDemand:
    """Describes the demand on a single item type.

    E.g. "5 Iron Plates per second".
    """

    def __init__(self, item_type, requested_rate=_F(0,1)):
        assert isinstance(item_type, ItemType)
        self.item_type = item_type
        assert isinstance(requested_rate, _F)
        self.requested_rate = requested_rate

    def required_factories(self):
        """How many factories are needed to supply at the requested rate?

        Returns either a Fraction or None. None is returned if (according to the
        XML) the item is "raw" and cannot be supplied by any factory.
        """
        return self.item_type.factories_needed_for(self.requested_rate)

    def required_ingredients_demand(self):
        """What our factories need to supply at the requested rate?

        This is either:
          - A list of ItemTypeDemand objects. Describes the ingredients needed,
            and the demand on those ingredients (how many per sec) which is
            needed by all factories (the number returned by
            self.required_factories), in order for them to be able to supply the
            requested item at the requested rate.
          - Or, None. None is returned if (according to the XML) the item is
            "raw" and cannot be supplied by any factory.
        """
        return self.item_type.ingredient_demand_needed_for(self.requested_rate)

    def __add__(self, other):
        """Return a new demand combined from two demands of the same item.

        E.g. 5 Iron Plates per second + 2 Iron Plates per second.
        """
        assert self.item_type is other.item_type
        combined_rate = self.requested_rate + other.requested_rate
        return ItemTypeDemand(self.item_type, combined_rate)

    def _get_label_lines(self, include_rate):
        """Generate a human-readable description of this demand.

        A *list* of lines of (plain) text is returned."""
        factories_count = self.required_factories()
        if factories_count is None:
            return [
                self.item_type._name,
                "Provide " + ("%.1f" % float(self.requested_rate)) + "/s"
            ]
        else:
            result = [
                self.item_type._name,
                "Build " + ("%.1f" % float(factories_count)) + " factories",
            ]
            if include_rate:
                result.append("to get " + ("%.1f" % float(self.requested_rate)) + "/s")
            return result

    def get_dot_nodespec(self, include_rate):
        """Generate a DOT statement with graph node representing this demand."""
        # Assumes each line contains safe text (doesn't require escaping).
        label = "\\n".join(self._get_label_lines(include_rate))
        return f'"{self.item_type._name}" [label="{label}"];'

    def _get_edge_label_lines(self, ingredient_demand):
        """Generate a human-readable description on a demand on an ingredient.

        A *list* of lines of (plain) text is returned. It takes an intermediate
        demand as the argument (before this demand will be summed up with other
        demands on this ingredient in the graph).
        """
        return [
            "%.1f" % float(ingredient_demand.requested_rate) + "/s",
        ]

    def get_dot_edgespecs(self):
        """Generate DOT statements with graph edges (links to ingredients).

        A *list* of DOT statements is returned."""
        ingredient_demands = self.required_ingredients_demand()
        if ingredient_demands is None:
            return []
        result = []
        for demand in ingredient_demands:
            label = "\\n".join(self._get_edge_label_lines(demand))
            result.append(f'"{self.item_type._name}" -> "{demand.item_type._name}" [dir=back, label="{label}"];')
        return result
 
class DemandGraph:
    """Describes a graph of ingredients required to satify a set of demands.

    There can be multiple "root" demands in this set. All ingredient demands
    will be summed up (there will be a single node per each ingredient type),
    but the edges will still represent the demands required by specific "parent"
    nodes.
    """

    def __init__(self, initial_demands = []):
        """Takes a list of initial demands (the "roots" for the tree)."""
        self.nodes = {}
        self.parent_ptrs = {}
        for demand in initial_demands:
            self.add_new_demand(demand)

    def add_new_demand(self, demand):
        """Append a new demand to the graph.

        This new demand, along with all its ingredient demands, will be
        cummulatively added up to the existing graph of demands.
        """
        assert isinstance(demand, ItemTypeDemand)
        key = demand.item_type._name
        if key in self.nodes:
            # Some demand for this item already exists. We'll need to merge.
            existing_demand = self.nodes[key]
            self.nodes[key] = existing_demand + demand
        else:
            self.nodes[key] = demand
            self.parent_ptrs[key] = {}
        demand = self.nodes[key]
        # Add all subdemands recursively.
        subdemands = demand.required_ingredients_demand()
        if subdemands is not None:
            for subdemand in subdemands:
                child = self.add_new_demand(subdemand)
                self.parent_ptrs[child.item_type._name][key] = demand
        return self.nodes[key]

    def _get_legend(self):
        """Generate an extra legend to be displayed along the graph.

        It returns a DOT statement.
        """
        label_lines = [
            "1.0 factory equals to:",
            "1.0 stone furnaces",
            "0.5 steel furnaces",
            "0.5 electric furnace",
            "2.0 assembling machines 1",
            "1.(3) assembling machines 2",
            "0.8 assembling machines 3",
        ]
        label = "\\l".join(label_lines)
        return "{ legend [shape=none, margin=0, label=\"" + label + "\\l\"]; }"

    def generate_dot_graph(self, file=None):
        """Generate a representation of the graph in the DOT language.

        A multiline string is returned."""
        lines = []
        lines.append("digraph G {")
        for node in self.nodes.values():


            include_rate_in_node_label = \
                len(self.parent_ptrs[node.item_type._name]) != 1
            lines.append("  " + node.get_dot_nodespec(
                include_rate=include_rate_in_node_label))
            for edgespec in node.get_dot_edgespecs():
                lines.append("  " + edgespec)
        lines.append("  " + self._get_legend())
        lines.append("}")
        return "\n".join(lines)
