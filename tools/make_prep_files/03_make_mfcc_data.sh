#!bin/bash

prep_out=$1

echo "command: $0 $@"

if [ $# != 1 ]; then
    echo "usage: make_mfcc_data.sh <prep_out>"
    echo "e.g. . ./make_mfcc_data.sh prep_out"
    echo "   prep_out: directory for output files"
    echo "             prep_out/data is required (make_prep_data.sh)"
    echo "             prep_out/data/data will be created for mfcc"
    exit 1;
elif [ ! -d ${prep_out}/data ]; then
    echo "${prep_out}/data is empty. Run make_prep_data.sh first"
    exit 1;
fi

. ./path.sh || exit 1;

# check directories
data_dir=$prep_out/data
conf_dir=conf
param_dir=param

[ ! -d ${conf_dir} ] && echo 'config does not exist' && exit 1;
[ ! -d param ] && echo 'param does not exist' && exit 1;
[ ! -L ./utils ] && ln -sf $KALDI_ROOT/egs/wsj/s5/utils ./utils
[ ! -L ./steps ] && ln -sf $KALDI_ROOT/egs/wsj/s5/steps ./steps

# source params
. $param_dir/dev
. $param_dir/mono

# extract mfcc
echo "Extracting... " `date`
export train_nj=1
steps/make_mfcc.sh \
    --nj $train_nj \
    --mfcc-config $conf_dir/mfcc.conf \
    --cmd "$train_cmd" \
    $data_dir
steps/compute_cmvn_stats.sh \
    $data_dir
utils/fix_data_dir.sh $data_dir

echo "Finished " `date`

