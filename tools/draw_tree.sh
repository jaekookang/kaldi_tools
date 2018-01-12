# Draw tree as .pdf file

# Usage: sh draw_tree.sh <phones.txt> <tree> <tree.pdf>
# e.g. sh draw_tree.sh ../data/phones.txt ../data/tree ../data/tree.pdf

# Outpot from dot should be resized to fit-in the entire tree

phones=$1
tree_raw=$2
tree_pdf=$3

kaldi_cmd=/home/kaldi/src/bin/draw-tree
# kaldi_cmd=draw-tree
$kaldi_cmd $phones $tree_raw | \
    dot -Tps -Gsize=8,10.5 | \
    ps2pdf - $tree_pdf