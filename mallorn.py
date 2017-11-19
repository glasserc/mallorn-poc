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


class DecisionNode(object):
    """A node in the decision tree.

    This is an abstract base class that just defines the interface for a node.
    """
    def __eq__(self, rhs):
        pass

    def get_outcome(self, query):
        pass


class OutcomeNode(object):
    """A "terminal" in the decision tree.

    This node serves all queries with a constant value."""
    def __init__(self, value):
        self.value = value

    def __eq__(self, rhs):
        return rhs.__class__ == self.__class__ and rhs.value == self.value

    def get_outcome(self, query):
        return Outcome(self.value)


def main():
    my_dt = DecisionTree({
        0: OutcomeNode("you did it"),
    })

    print(my_dt)
    print(my_dt.get_outcome({"product": "Firefox", "version": "45.0.1", "locale": "fr"}).value)


if __name__ == '__main__':
    main()
