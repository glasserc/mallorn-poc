"""
mallorn: a POC for a decision tree architecture for Balrog

See README for more info.
"""

import subprocess

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
        """Return a graphviz digraph representing this decision tree."""
        lines = [
            'node [shape=diamond];',
            'start [shape=box];',
            'start -> node_0;',
        ]

        for node_id, node in self.nodes.items():
            lines.append(node.render_graphviz(node_id))

        lines = ['digraph G {'] + lines + ['}']
        return '\n'.join(lines)

    def get_query_for_outcome(self, node_id):
        """DFS the decision tree to find all paths that lead to node_id."""
        seen = [0]
        current_query = {}
        success_paths = []
        self.dfs_from_node_with_target(0, seen, current_query, success_paths, node_id)
        return success_paths

    def dfs_from_node_with_target(self, current_id, current_path, current_query, success_paths, target):
        node = self.nodes[current_id]
        for (query, next_node) in node.outgoing_edges():
            if next_node in current_path:
                # We've already visited it
                continue

            new_query = intersection(query, current_query)
            if not new_query:
                # There's no way to take this edge given the path we
                # took to get here.
                continue

            if next_node == target:
                # This query gets us to what we want!
                success_paths.append(new_query)
                continue

            # Otherwise continue the DFS
            new_path = current_path + [current_id]
            self.dfs_from_node_with_target(next_node, current_path, new_query, success_paths, target)


def intersection(query1, query2):
    """Merge two queries, returning one that will satisfy both queries.

    If a key is missing from a query, it means any value at all is acceptable.

    If incompatible values are present in the two queries, return
    None, indicating that the intersection is empty.

    """
    ret = query2.copy()
    for k, v in query1.items():
        if k not in ret:
            # query2 doesn't care about this, so just use query1's value
            ret[k] = v
            continue

        if ret[k] == v:
            # OK, both queries want the same thing
            continue

        # The queries want different things.
        # FIXME: actually implement this case
        # Pay no attention to the man behind the curtain...
        if k == 'version':
            if v == '==55.0.3' and ret[k] == '<56':
                ret[k] = '==55.0.3'
                continue
            elif v == '!=55.0.3' and ret[k] == '<56':
                ret[k] = '<56 and !=55.0.3'
                continue
            if v == '==54.0.1' and ret[k] == '<56 and !=55.0.3':
                ret[k] = '==54.0.1'
                continue
            elif v == '!=54.0.1' and ret[k] == '<56 and !=55.0.3':
                ret[k] = '<56 and !=55.0.3 and !=54.0.1'
                continue

        return None

    return ret


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

    def render_graphviz(self, node_id):
        """Render a graphviz fragment for this node.

        This should return a string describing this node and its links
        to other nodes.

        By convention, all nodes are represented in graphviz as
        vertices with IDs of the form node_id.

        It's considered good practice to have the node label include
        the node ID for informational purposes.

        Decision points should be represented as shape=diamond
        (currently the graph-wide default). Outcomes should be
        represented as shape=ellipse.

        """
        pass

    def outgoing_edges(self):
        """Return a list of (query, next_node) pairs.

        Each pair represents a possible next step in the decision
        tree, as well as the required query that would be necessary to
        get there.
        """
        return []


def label_with_id(node_id, label):
    """Get a graphviz label which is prefixed with a node ID.

    This uses the Graphviz "HTML" format for labels to call out the
    node ID in a way that is visually distinct from the remaining content.

    You can make a more complicated label by passing a label which is
    itself HTML.
    """
    return '<<b><u>{}</u></b><br/>{}>'.format(
        node_id, label)


def graphviz_vertex_with_id(node_id, label):
    """Get a graphviz node description given the ID and label.

    This describes the Graphviz vertex by itself and is appropriate if
    you have a DecisionNode that isn't an outcome and therefore
    doesn't have any interesting formatting requirements.

    This generates the node's label using label_with_node_id, which
    see for more information.

    """
    return 'node_{} [label={}];'.format(node_id, label_with_id(node_id, label))


def safe_node_id(node_id):
    """Helper to sanitize graphviz node IDs.

    Hyphens (-) are not allowed as part of a node ID.

    We also prefix all node IDs with "node_".
    """
    return 'node_{}'.format(str(node_id).replace('-', '_'))


def edge(node_src, node_dest, label):
    """Helper to generate graphviz fragments for edges."""
    return '{} -> {} [label="{}"];'.format(
        safe_node_id(node_src),
        safe_node_id(node_dest),
        label
    )


class OutcomeNode(DecisionNode):
    """A "terminal" in the decision tree.

    This node serves all queries with a constant value."""
    def __init__(self, value):
        self.value = value

    def get_outcome(self, query):
        return Outcome(self.value)

    def render_graphviz(self, node_id):
        label = label_with_id(node_id, self.value)
        return '{} [shape=ellipse,label={}];'.format(
            safe_node_id(node_id), label)


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

    def render_graphviz(self, node_id):
        label = 'version &lt; {}?'.format(self.cutoff)
        lines = [graphviz_vertex_with_id(node_id, label)]
        lines.append(edge(node_id, self.less_node, 'yes (lt)'))
        lines.append(edge(node_id, self.greater_or_equal_node, 'no (gte)'))
        return '\n'.join(lines)

    def outgoing_edges(self):
        return [
            ({"version": "<{}".format(self.cutoff)}, self.less_node),
            ({"version": ">={}".format(self.cutoff)}, self.greater_or_equal_node)
        ]


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

    def render_graphviz(self, node_id):
        lines = [graphviz_vertex_with_id(node_id, 'check version')]
        lines.append(edge(node_id, self.success_node, '= {}'.format(self.match)))
        lines.append(edge(node_id, self.failure_node, 'otherwise'))
        return '\n'.join(lines)

    def outgoing_edges(self):
        return [
            ({"version": "=={}".format(self.match)}, self.success_node),
            ({"version": "!={}".format(self.match)}, self.failure_node)
        ]


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

    def render_graphviz(self, node_id):
        lines = [graphviz_vertex_with_id(node_id, 'check OS')]
        lines.append(edge(node_id, self.windows_node, 'windows'))
        lines.append(edge(node_id, self.linux_node, 'linux'))
        lines.append(edge(node_id, self.macos_node, 'macos'))
        return '\n'.join(lines)

    def outgoing_edges(self):
        return [
            ({"os": "windows"}, self.windows_node),
            ({"os": "linux"}, self.linux_node),
            ({"os": "macos"}, self.macos_node),
        ]


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

    def render_graphviz(self, node_id):
        lines = [graphviz_vertex_with_id(node_id, 'check product')]
        lines.append(edge(node_id, self.success_node, '= {}'.format(self.product)))
        lines.append(edge(node_id, self.failure_node, 'otherwise'))
        return '\n'.join(lines)

    def outgoing_edges(self):
        return [
            ({"product": "=={}".format(self.product)}, self.success_node),
            ({"product": "!={}".format(self.product)}, self.failure_node),
        ]


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

    def render_graphviz(self, node_id):
        lines = [graphviz_vertex_with_id(node_id, 'cpu arch')]
        lines.append(edge(node_id, self.node_32bit, '32-bit'))
        lines.append(edge(node_id, self.node_64bit, '64-bit'))
        return '\n'.join(lines)

    def outgoing_edges(self):
        return [
            ({"cpuarch": 32}, self.node_32bit),
            ({"cpuarch": 64}, self.node_64bit),
        ]


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

    def render_graphviz(self, node_id):
        lines = [graphviz_vertex_with_id(node_id, 'os arch')]
        lines.append(edge(node_id, self.node_32bit, '32-bit'))
        lines.append(edge(node_id, self.node_64bit, '64-bit'))
        return '\n'.join(lines)

    def outgoing_edges(self):
        return [
            ({"osarch": 32}, self.node_32bit),
            ({"osarch": 64}, self.node_64bit),
        ]


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

    def render_graphviz(self, node_id):
        lines = [graphviz_vertex_with_id(node_id, 'locale')]
        lines.append(edge(node_id, self.success_node, ', '.join(self.locales)))
        lines.append(edge(node_id, self.failure_node, 'otherwise'))
        return '\n'.join(lines)

    def outgoing_edges(self):
        return [
            # FIXME: it would be great to have a definitive list of
            # locales so that we could just use a complete list
            ({"locale": "in {}".format(', '.join(self.locales))}, self.success_node),
            ({"locale": "any but {}".format(', '.join(self.locales))}, self.failure_node),
        ]


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

    def render_graphviz(self, node_id):
        lines = [graphviz_vertex_with_id(node_id, self.key)]
        lines.append(edge(node_id, self.success_node, self.value))
        lines.append(edge(node_id, self.failure_node, 'otherwise'))
        return '\n'.join(lines)

    def outgoing_edges(self):
        return [
            # FIXME: it would be great to have a definitive list of
            # locales so that we could just use a complete list
            ({self.key: "=={}".format(self.value)}, self.success_node),
            ({self.key: "!={}".format(self.value)}, self.failure_node),
        ]


########## End decision nodes! ############
# OK let's get to the good stuff.
def try_render_graphviz(dt, filename_base):
    dot_filename = '{}.dot'.format(filename_base)
    png_filename = '{}.png'.format(filename_base)
    with open(dot_filename, 'w') as f:
        f.write(dt.render_graphviz())

    try:
        subprocess.check_call(
            ['dot', dot_filename, '-Tpng', '-o', png_filename]
        )
    except OSError:
        # Guess graphviz isn't installed on this computer.
        # Silently don't render a png.
        #
        # check_call raises CalledProcessError if dot returned
        # nonzero, so that isn't handled (bubbles up).
        pass


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
        9: CPUArchitectureNode(11, 10),
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

        16: ArbitraryMatcherNode('JAWS', '1', 17, 6),
        # Incompatible JAWS. Ship 56.0.2.
        # N.B. The real spreadsheet says that <56.0.2 get shipped
        # 56.0.2, and 56.0.2 gets shipped nothing. This seems kind of
        # obvious to me, but maybe the client doesn't know how to do
        # this. Anyhow, it's easy to add, but for simplicity I'm
        # skipping it.
        17: OutcomeNode('firefox56.0.2-jaws-incompatible'),

        # 32-bit OS, 64-bit processor. Trying to migrate.
        40: ArbitraryMatcherNode('JAWS', 1, 41, 44),
        # JAWS incompatible. We migrate but only on 56.0.
        41: VersionExactNode('56.0', 42, 17),
        42: OutcomeNode('firefox56.0.2-lzma-migration'),

        # JAWS is OK. We only migrate 56.0.
        44: VersionExactNode('56.0', 45, 6),
        45: LocaleMatcherNode(VARIANT_A_AND_B, 46, 47),
        46: OutcomeNode('firefox57-lzmacomplete-wnp'),
        47: OutcomeNode('firefox57-lzmacomplete-nownp'),

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
    try_render_graphviz(my_dt, 'rules')

    print('Who gets firefox57-lzma-nownp?')
    for query in my_dt.get_query_for_outcome(8):
        print(', '.join('{}: {}'.format(k.title(), v) for k, v in sorted(query.items())))


if __name__ == '__main__':
    main()
