#!bin/bash

prep_out=$1

echo "command: $0 $@"

if [ $# != 1 ]; then
    echo "usage: make_lang.sh <prep_out>"
    echo "e.g. . ./make_prep_data.sh prep_out"
    echo "   prep_out: directory for output files"
    echo "             prep_out/prep is required (make_prep_data.sh)"
    echo "             prep_out/lang will be created"
    exit 1;
elif [ ! -d ${prep_out}/data ]; then
    echo "${prep_out}/data is empty. Run make_prep_data.sh first"
    exit 1;
fi

. ./path.sh || exit 1;

data_dir=${prep_out}/data
created=${prep_out}/created
lang_dir=${prep_out}/lang

for x in $created $lang_dir ; do
    if [ ! -d $x ]; then mkdir -p $x
    else rm -r $x; mkdir $x
    fi
done

# create symlink for utils, steps
[ ! -L ./utils ] && ln -sf $KALDI_ROOT/egs/wsj/s5/utils ./utils
[ ! -L ./steps ] && ln -sf $KALDI_ROOT/egs/wsj/s5/steps ./steps

# copy lexicon.txt
cp lexicon.txt $data_dir
# remove <unk>
sed -i '/<unk>/d' $data_dir/lexicon.txt
utils/fix_data_dir.sh $data_dir
# make spk2utt
utils/utt2spk_to_spk2utt.pl $data_dir/utt2spk > $data_dir/spk2utt
# make nonsilence_phones.txt
# the gap btw word and pronunciation is a space not a tab
cut -d ' ' -f 2- $data_dir/lexicon.txt | tr ' ' '\n' | sed '/^$/d' | sort -u > $created/nonsilence_phones.txt
# remove sil
sed -i '/sil/d' $created/nonsilence_phones.txt
# add sil to options_silence.txt
echo "sil" > $created/optional_silence.txt
# make silence_phones.txt
echo -e "sil\n<unk>" > $created/silence_phones.txt
# make extra_questions.txt, by grouping same stress num
cat $created/silence_phones.txt| awk '{printf("%s ", $1);} END{printf "\n";}' > $created/extra_questions.txt || exit 1;
cat $created/nonsilence_phones.txt | perl -e 'while(<>){ foreach $p (split(" ", $_)) {  $p =~ m:^([^\d]+)(\d*)$: || die "Bad phone $_"; $q{$2} .= "$p "; } } foreach $l (values %q) {print "$l\n";}' >> $created/extra_questions.txt || exit 1;    
# add <unk> <unk> at first line of lexicon.txt
ed -s $data_dir/lexicon.txt <<< $'1i\n<unk> <unk>\n.\nwq'
cp $data_dir/lexicon.txt $created

utils/prepare_lang.sh \
       $created "<unk>" \
       $created/tmp \
       $lang_dir

# make LM (n-gram)
$KALDI_ROOT/tools/srilm/bin/i686-m64/ngram-count -text $data_dir/textraw -lm $lang_dir/lm.arpa
cat $lang_dir/lm.arpa | $KALDI_ROOT/src/lmbin/arpa2fst --disambig-symbol=#0 --read-symbol-table=$lang_dir/words.txt - $lang_dir/G.fst
$KALDI_ROOT/src/fstbin/fstisstochastic $lang_dir/G.fst

utils/fix_data_dir.sh $data_dir

##### End of the preparation #####
echo "Finished: " `date`
# exit 0;



