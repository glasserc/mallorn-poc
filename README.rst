Mallorn: a proposed design for Balrog
=====================================

Mallorn is just a throwaway name for this proof-of-concept demo which
structures the internal workings of a `Balrog <https://github.com/mozilla/balrog/>`_-like service as a
decision tree/behavior tree.

(Refs https://en.wikipedia.org/wiki/Middle-earth_plants#Mallorn)

Background
==========

Balrog as it currently stands uses a "linear" set of rules to respond
to a "what update do I need?" query (henceforth called an "update
query") from various clients. These rules are represented using rows
in a MySQL database. Each rule contains some attributes which it can
"match" and some outcomes for requests which match it. For example, a
rule might be like "product=Firefox, version=45, locale=fr -> version
52 partial update". Attributes that are not specified in the rule are
considered irrelevant; any update query will match this rule
regardless of e.g. its "architecture" attribute.

An update query is serviced in this paradigm by finding all the rules
that could apply using a database request, picking the one with the
highest priority, and serving its outcome. As an example, take this
set of rules:

+---------+--------+-------+------+---------------------+
|Priority |Product |Version|Locale|Outcome              |
+---------+--------+-------+------+---------------------+
|400      |Firefox |45     |fr    |52 partial update    |
+---------+--------+-------+------+---------------------+
|300      |Firefox |45     |      |46.0.1 partial update|
+---------+--------+-------+------+---------------------+
|200      |Firefox |52     |      |57 partial update    |
+---------+--------+-------+------+---------------------+
|0        |Firefox |       |      |57 complete update   |
+---------+--------+-------+------+---------------------+

Given the query "product=Firefox, version=52, locale=fr", we follow
the third rule (with priority=200) and tell the client to apply the
partial update for version 57. Given the query "product=Firefox,
version=49, locale=fr", we follow the last rule (with priority 0) and
tell the client to apply the version 57 complete update.

Motivation
==========

Although each rule in this system is straightforward to understand and
apply, together the whole system is quite difficult to
fathom. Examining a single rule is insufficient because what users it
affects is only partially determined by that rule itself, and
partially determined by what higher-priority rules take
precedence. For example, the rule with priority=300 applies to all
users with Firefox 45 *except for those with locale=fr because of rule
400*. Changing this rule from version=45 to version=46 not only
changes the population that it affects; it also changes the
populations that hit lower-priority rules down the line. This hurts
the composability of rulesets, which means that changes to a single
rule are difficult to evaluate -- an entire ruleset is the smallest
unit of reviewability.

One approach to try to improve comprehensibility of the system is to
move from a flat, imperative model represented by this series of rules
towards a hierarchical, functional model, namely one based around
decision trees.

Idea
====

Instead of Balrog evaluating an update query against a list of rules,
instead it can evaluate it against a decision tree. A decision tree
can either be an outcome, in which case we serve that outcome, or a
decision point that examines one attribute of a request and, depending
on that attribute, forwards to other decision trees. An example
decision point might look at platform, with ``linux`` queries going
towards a Linux decision tree, and other queries going towards a
"fallback" decision tree.

The advantages of this design are:

- It maps more naturally to how relman naturally conceptualize the
  Balrog problem domain -- instead of thinking about what rules they
  have to write, they think about the population of users and divide
  them according to various criteria, "routing" them towards certain
  outcomes.

- At each point in the decision tree, it's clear what population
  arrives there -- just follow the branches.

- Individual decision points are quite simple, because they consider
  only one individual variable, without regard to the set of variables
  that brought a user to this point.

Evaluation
==========

In order to clarify the design, both for myself and for others, I have
put together this little proof of concept (POC) which serves to illustrate
the idea. The goal of the POC was to illustrate:

- Why the design is worth pursuing. This takes the form of a couple of
  neat features which would be quite difficult to write in Balrog, but
  are rather easy to write using the tree-based approach.

- How such an inherently nested design might serialize to/from a
  database.

- How "edits" to such a design might look. Because Balrog is both a
  decision tree and a code repository, it's worth focusing on
  individual changes and how those might be represented.

Things that the POC was not meant to illustrate:

- Clean API. Users of Balrog today do not write code programmatically
  (although perhaps they should). As a result, I made no effort to
  find a beautiful code-level API. Indeed, code quality leaves much to
  be desired -- sorry!

- The complete or correct set of decision points. The ones I have are
  just because they were interesting to me at the time. Hopefully the
  idea still makes sense even if the specific set of decision points I
  chose are wrong.

- Efficiency. I am convinced that this design could be made as
  efficient or moreso than the Balrog design, but that wasn't my aim
  here. The biggest load on Balrog are update queries, but as they are
  read-only operations, they are inherently quite scalable (not to
  mention cacheable), so we already have a path to scalability if we
  really need it.

Result
======

Please see mallorn.py, which contains in one giant file code
representing a decision tree "engine" as well as a sample set of rules
taken from the "State of updates once 57 ships" document. When you run
this file:

- A graphviz graph representing the decision tree is generated. (If
  you have graphviz installed, this graph file is rendered as a PNG.)

- A change to the sample rules is considered. "Considered" here means
  that a human-readable description of this change is printed to standard output.

- The rule set (with the change) is turned into a list of flat "rows",
  suitable for storing in a database (the INSERT query is printed to
  standard output), and then deserialized back into a decision tree
  (which is compared with the original to demonstrate accuracy).
