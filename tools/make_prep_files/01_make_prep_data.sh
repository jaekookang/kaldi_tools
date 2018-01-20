#!bin/bash

prep_in=$1
prep_out=$2

echo "$0 $@"

if [ $# != 2 ]; then
    echo "usage: make_prep_data.sh <prep_in> <prep_out>"
    echo "e.g. . ./make_prep_data.sh prep_in prep_out"
    echo "   prep_in: directory for .wav & .txt files"
    echo "   prep_out: directory for output files"
    echo "             prep_out/prep will be created"
    echo "   - prep_out/data/text"
    echo "   - prep_out/data/textraw"
    echo "   - prep_out/data/wav.scp"
    echo "   - prep_out/data/utt2spk"
    exit 1;
fi


# check directory and create new files
prep_out=${prep_out}/data
[ -d ${prep_out} ] && rm -rf ${prep_out}/*
[ ! -d ${prep_out} ] && mkdir -p ${prep_out}
preplist=(${prep_out}/wav.scp ${prep_out}/text ${prep_out}/utt2spk ${prep_out}/textraw)
for d in ${preplist[@]}; do
    [ -f $d ] && rm $d || touch $d
done

# make {wav,txt} list
wavlist=($(find ${prep_in}/* -name "*.wav"))
txtlist=($(find ${prep_in}/* -name "*.txt"))
# check directory if empty or not
[ ! -d $1 ] && echo "$1 is empty" && exit 1;
# check wavlist == txtlist
[ ${#wavlist[@]} -ne ${#txtlist[@]} ] && echo "Number of .wav & .txt files not equal" && exit 1;

for ((i=0;i<${#wavlist[@]};++i)); do
    wname=$(basename ${wavlist[$i]} .wav)
    tname=$(basename ${txtlist[$i]} .txt)
    # check wav == txt file
    if [ "$wname" == "$tname" ]; then
    	uttID=$wname
	spkID=SPEAKER # assume the same speaker, edit if necessary
    	txt=$(cat ${txtlist[$i]})
    	# textraw
    	echo ${txt} >> ${prep_out}/textraw
	# text
	echo ${uttID} ${txt} >> ${prep_out}/text
    	# wav.scp
    	echo ${uttID} ${wavlist[$i]} >> ${prep_out}/wav.scp
	# utt2spk
	echo ${uttID} ${spkID} >> ${prep_out}/utt2spk
    else
    	echo ".wav & .txt files not matching or missing"
    	exit 1;
    fi
done
echo "Files created in ${prep_out}"

