#!/bin/bash
set -euo pipefail

# Assumption: Called from logcheck folder
if [[ $(basename $(pwd)) != logcheck ]]
then
	echo "Call from logcheck folder!"
	exit
fi

#Split up for execution time reasons
# minimums="5 10 20 50 75 100 200"
minimums="50"

for min in $minimums; do
#	 filtering_path="../repos/python/filter/300repos_min"$min"_max1000000"
	filtering_path="../repos/python/filter/300repos_minus_nonlogged_min"$min"_max1000000"
	
	# output_path="features/174repos_min"$min"_max1000000_new_keyword_"
	# output_path="features/300repos_min"$min"_max1000000_"
#	 output_path="features/300_min"$min"_parallelized_"
	# output_path="features/174repos_min"$min"_max1000000_counts_"
#	output_path="features/174repos_min"$min"_max1000000_node_len_"
#	output_path="features/174_min"$min"_num_children_depth_from_def_"
	output_path="features/174_min"$min"_alt_siblings_"

	# echo $filtering_path
	# echo $output_path
#	echo expanded
#	python3 logcheck.py -e -a -o $output_path"expanded.csv" $filtering_path
	 echo zhenhao
	 python3 logcheck.py -e -z -o $output_path"zhenhao.csv" $filtering_path
done