#! /usr/bin/env python
# usage: python minVAR_reroot.py <tree_file>

from Tree_extend import minVAR_Tree
from sys import argv
from os.path import splitext

tree_file = argv[1]
base_name,ext = splitext(tree_file)


a_tree = minVAR_Tree(tree_file=tree_file)
head_id, tail_id, edge_length, x = a_tree.Reroot()
print "Head: " + str(head_id) + "\nTail: " + str(tail_id) + "\nEdge_length: " + str(edge_length) + "\nx: " + str(x)
a_tree.tree_as_newick(outfile=base_name+"_minVAR_rooted"+ext,restore_label=True)