"""
mallorn: a POC for a decision tree architecture for Balrog

See README for more info.
"""


class DecisionTree(object):
    """An entire decision tree.

    This is the main entry point of the engine.
    """
    def __init__(self, nodes):
        """Build a new DecisionTree.

        :param nodes: a dict of node ID -> DecisionNode instances.
            By convention, node ID 0 is the "start" point.
        """
        self.nodes = nodes

    def __eq__(self, rhs):
        return self.nodes == rhs.nodes

    def get_outcome(self, query):
        """Get the outcome for this decision tree.

        This might represent the update served in response to an
        update query.

        :param query: a dict of information for use in the decision"""
        current_node_id = 0
        while True:
            node = self.nodes[current_node_id]
            result = node.get_outcome(query)
            if isinstance(result, Outcome):
                return result

            # Otherwise, result is a Continue.
            current_node_id = result.next_node_id


    def render_graphviz(self):
        pass


class Outcome(object):
    """A decision tree's Outcome.

    This is a wrapper around an arbitrary value.

    A DecisionNode can return this to signal that a get_outcome has
    succeeded and to stop processing.

    """
    def __init__(self, value):
        self.value = value


class Continue(object):
    """A decision tree's next step.

    A DecisionNode can return this to signal that a get_outcome is
    incomplete and needs to be continued at a different point in the
    decision tree.

    """
    def __init__(self, next_node_id):
        self.next_node_id = next_node_id


############# Decision node subclasses #####################
# I went a bit overboard here to try to match the Google sheet.
# In principle, we can define one of these for each variable in a
# query, or not, depending on what users want.
class DecisionNode(object):
    """A node in the decision tree.

    This is an abstract base class that just defines the interface for a node.
    """
    def __eq__(self, rhs):
        # This is kind of a hack but it saves me from having to define
        # the __eq__ for all nodes, which are all basically the same.
        return rhs.__class__ == self.__class__ and self.__dict__ == rhs.__dict__

    def get_outcome(self, query):
        """Handle a given query.

        A DecisionNode should always return Continue instances, except
        for the OutcomeNode subclass, which should always return
        Outcome instances.

        """
        pass


class OutcomeNode(DecisionNode):
    """A "terminal" in the decision tree.

    This node serves all queries with a constant value."""
    def __init__(self, value):
        self.value = value

    def get_outcome(self, query):
        return Outcome(self.value)


class VersionCutoffNode(DecisionNode):
    """A node that tries to examine the query's version."""
    def __init__(self, cutoff, less_node, greater_or_equal_node):
        self.cutoff = cutoff
        self.less_node = less_node
        self.greater_or_equal_node = greater_or_equal_node

    def get_outcome(self, query):
        version = query['version']
        if version < self.cutoff:
            return Continue(self.less_node)
        else:
            return Continue(self.greater_or_equal_node)


class VersionExactNode(DecisionNode):
    """Another node that examines the query's version.

    Unlike VersionCutoffNode, this one looks for specific version numbers."""
    def __init__(self, match, success_node, failure_node):
        self.match = match
        self.success_node = success_node
        self.failure_node = failure_node

    def get_outcome(self, query):
        if query['version'] == self.match:
            return Continue(self.success_node)
        else:
            return Continue(self.failure_node)


# Conceptually, every decision node is an on/off decision point like
# VersionCutoffNode, but some decision nodes combine several
# possibilities into one node for convenience.
class OperatingSystemNode(DecisionNode):
    """A node that tries to match the operating system of a query.

    Operating systems fall within a few well-known values, and it's
    common to treat each one differently. As a result, the caller is
    required to pass a node for each one.

    """
    def __init__(self, windows_node, linux_node, macos_node):
        self.windows_node = windows_node
        self.linux_node = linux_node
        self.macos_node = macos_node

    def get_outcome(self, query):
        os = query['os']
        if os == 'windows':
            return Continue(self.windows_node)
        elif os == 'linux':
            return Continue(self.linux_node)
        else:
            return Continue(self.macos_node)


class ProductNode(DecisionNode):
    """A node that tries to match the "product" of a query.

    Queries matching this node's product are routed to a "success"
    node. Other queries are routed to a "failure" node.

    """
    def __init__(self, product, success_node, failure_node):
        self.product = product
        self.success_node = success_node
        self.failure_node = failure_node

    def get_outcome(self, query):
        if query['product'] == self.product:
            return Continue(self.success_node)
        else:
            return Continue(self.failure_node)


class CPUArchitectureNode(DecisionNode):
    """A node that checks for 32-bit and 64-bit hardware."""
    def __init__(self, node_32bit, node_64bit):
        # Because 32bit_node isn't a valid variable name...
        self.node_32bit = node_32bit
        self.node_64bit = node_64bit

    def get_outcome(self, query):
        bits = query['cpuarch']
        if bits == 32:
            return Continue(self.node_32bit)
        else:
            return Continue(self.node_64bit)


class OSArchitectureNode(DecisionNode):
    """A node that checks fro 32-bit and 64-bit OSes."""
    def __init__(self, node_32bit, node_64bit):
        self.node_32bit = node_32bit
        self.node_64bit = node_64bit


    def get_outcome(self, query):
        bits = query['osarch']
        if bits == 32:
            return Continue(self.node_32bit)
        else:
            return Continue(self.node_64bit)


class LocaleMatcherNode(DecisionNode):
    """A node that checks for a set of locales.

    Matching any of the given locales routes you to the success_node.
    """
    def __init__(self, locales, success_node, failure_node):
        self.locales = locales
        self.success_node = success_node
        self.failure_node = failure_node

    def get_outcome(self, query):
        if query['locale'] in self.locales:
            return Continue(self.success_node)
        else:
            return Continue(self.failure_node)


class ArbitraryMatcherNode(DecisionNode):
    """A node that checks for a specific value of a specific variable.

    This is kind of the "back door" in the system that supports
    one-off things like JAWS.

    If we find that a specific ArbitraryMatcherNode is used a lot, we
    should turn it into its own DecisionNode subclass.
    """
    def __init__(self, key, value, success_node, failure_node):
        self.key = key
        self.value = value
        self.success_node = success_node
        self.failure_node = failure_node

    def get_outcome(self, query):
        if query[self.key] == self.value:
            return Continue(self.success_node)
        else:
            return Continue(self.failure_node)


########## End decision nodes! ############
# OK let's get to the good stuff.

def main():
    VARIANT_A_AND_B = set([
        'ast', 'bg', 'bs', 'cak', 'cs', 'cy', 'da', 'de', 'dsb', 'en-GB',
        'en-US', 'eo', 'es-AR', 'es-CL', 'es-ES', 'es-MX', 'et', 'fa', 'fr',
        # ... and all the others..
    ])

    my_dt = DecisionTree({
        0: ProductNode('Firefox', 1, "fennec-outcome"),
        # I thought node IDs being numeric would be easiest, but I
        # guess they don't have to be..
        "fennec-outcome": OutcomeNode("Newest Fennec"),

        # Actually, I thought OperatingSystemNodes would always have
        # three different nodes, but they don't have to...
        1: OperatingSystemNode(9, 2, 2),

        # Linux, Mac
        2: VersionCutoffNode('56', 3, 6),
        # Less than 56 -- bz2 partial
        3: LocaleMatcherNode(VARIANT_A_AND_B, 4, 5),
        # Variant A and B: gets WNP
        4: OutcomeNode('firefox57-bz2-wnp'),
        # Other locales: don't get WNP
        5: OutcomeNode('firefox57-bz2-nownp'),

        # 56 and up -- lzma partial
        6: LocaleMatcherNode(VARIANT_A_AND_B, 7, 8),
        7: OutcomeNode('firefox57-lzma-wnp'),
        8: OutcomeNode('firefox57-lzma-nownp'),

        # Windows
        9: CPUArchitectureNode(14, 10),
        # 64-bit processor. Check if 32-bit OS.
        # FIXME: no idea what "eligible" means here; just ignoring it
        10: OSArchitectureNode(40, 11),

        # 32-bit processor (so therefore 32-bit OS), or 64-bit
        # processor with 64-bit OS, or otherwise not trying to migrate
        11: VersionCutoffNode('56', 12, 16),
        # Ship 56
        12: VersionExactNode('55.0.3', 14, 13),
        13: VersionExactNode('54.0.1', 14, 15),
        14: OutcomeNode('firefox56-bz2partial'),
        15: OutcomeNode('firefox56-bz2complete'),

        16: ArbitraryMatcherNode('JAWS', '1', 17, 18),
        # Incompatible JAWS. Ship 56.0.2.
        # N.B. The real spreadsheet says that <56.0.2 get shipped
        # 56.0.2, and 56.0.2 gets shipped nothing. This seems kind of
        # obvious to me, but maybe the client doesn't know how to do
        # this. Anyhow, it's easy to add, but for simplicity I'm
        # skipping it.
        17: OutcomeNode('firefox56.0.2-jaws-incompatible'),

        # JAWS-compatible, 56
        18: LocaleMatcherNode(VARIANT_A_AND_B, 7, 8),

        # 32-bit OS, 64-bit processor. Trying to migrate.
        40: ArbitraryMatcherNode('JAWS', 1, 41, 44),
        # JAWS incompatible. We migrate but only on 56.0.
        41: VersionExactNode('56.0', 42, 17),
        42: OutcomeNode('firefox56.0.2-lzma-migration'),

        # JAWS is OK. We only migrate 56.0.
        44: VersionExactNode('56.0', 45, 48),
        45: LocaleMatcherNode(VARIANT_A_AND_B, 46, 47),
        46: OutcomeNode('firefox57-lzmacomplete-wnp'),
        47: OutcomeNode('firefox57-lzmacomplete-nownp'),

        # Don't migrate anyone else.
        48: LocaleMatcherNode(VARIANT_A_AND_B, 7, 8),
    })

    print(my_dt)
    query = {
        "product": "Firefox",
        "os": "windows",
        "cpuarch": 64,
        "osarch": 32,
        "version": "56.0.1",
        "locale": "fr",
        "JAWS": 0,
    }
    print(my_dt.get_outcome(query).value)


if __name__ == '__main__':
    main()
