# get_hmm_gmm.py

import numpy as np
import os
import re
import pdb
import pickle
from time import gmtime, strftime


class GetParam():
    '''
    GetParam object organizes HMM & GMM parameters for silence and nonsilence phones

    tested only on Librispeech output

    # TODO: Combine two attributes (Obj.pdf, Obj.gmm) into Obj.gmm

    Note:
    - gmm_id: same as pdf id

    Input:
    - mdl_txt:
    - trans_txt:
    - phones_txt:
    - sets_txt:

    Output:
    - HMM dictionary (HMM parameters)
    - GMM dictionary (GMM parameters)
    - pdf-id dictionary (pdf-if --> phone)

    '''

    def __init__(self, mdl_txt, trans_txt, phones_txt, sets_txt, save_dir):
        self.mdl_txt = mdl_txt
        self.trans_txt = trans_txt
        self.phones_txt = phones_txt
        self.sets_txt = sets_txt
        self.save_dir = save_dir

        # Load data
        self.load_phones_txt()
        self.load_trans_txt()
        self.load_final_txt()
        self.load_sets_txt()

    def load_phones_txt(self):
        '''
        Open phones.txt file
        '''
        with open(self.phones_txt, 'r') as f:
            phones_raw = f.read().splitlines()
        self.ph2idx = {}
        self.idx2ph = {}
        for line in phones_raw:
            ph, idx = line.split()
            self.ph2idx[ph] = int(idx)
            self.idx2ph[int(idx)] = ph
        return print('{} is loaded'.format(self.phones_txt))

    def load_trans_txt(self):
        '''
        Open trans_prob.txt file
        '''
        with open(self.trans_txt, 'r') as f:
            self.trans_raw = f.read().splitlines()
        return print('{} is loaded'.format(self.trans_txt))

    def load_sets_txt(self):
        '''
        Open sets.txt file
        '''
        with open(self.sets_txt, 'r') as f:
            tmp = f.read().splitlines()
            for ph in self.sil_phones:
                idx = self.get_index(tmp, ph)
                if idx:
                    del tmp[idx[0]]
            self.sets_raw = [l.split() for l in tmp]
        return print('{} is loaded'.format(self.sets_txt))

    def load_final_txt(self):
        '''
        Open final.txt file (converted from final.mdl)
        output:
        nonsil_phones: a list of nonsilence phones
        nonsil_phones_id: a list of indices of nonsilence phones
        state
        '''
        with open(self.mdl_txt, 'r') as f:
            mdl_raw = f.read().splitlines()

        # Get nonsilence/silence phones
        ForPhones = self.get_index(mdl_raw, '<ForPhones>')
        self.nonsil_phones_id = [int(i)
                                 for i in mdl_raw[ForPhones[0] + 1].split()]
        self.nonsil_phones = [self.idx2ph[i] for i in self.nonsil_phones_id]
        self.sil_phones_id = [int(i)
                              for i in mdl_raw[ForPhones[1] + 1].split()]
        self.sil_phones = [self.idx2ph[i] for i in self.sil_phones_id]

        # Get GMM info
        self.gmm = {}
        NUMPDFS = self.get_index(mdl_raw, '<NUMPDFS>')[0]
        total_gmm = int(re.search('\<NUMPDFS\> (.*) \<',  # number of Gaussian components
                                  mdl_raw[NUMPDFS]).group(1))
        DIMENSIONS = self.get_index(mdl_raw, '<DIMENSION>')[0]
        dim = int(re.search('\<DIMENSION\> (.*) \<NUMPDFS>',  # input dimension; e.g. 39
                            mdl_raw[DIMENSIONS]).group(1))
        WEIGHTS = self.get_index(mdl_raw, '<WEIGHTS>')
        MEANS_INVVARS = [
            i + 1 for i in self.get_index(mdl_raw, '<MEANS_INVVARS>')]
        INV_VARS = [i + 1 for i in self.get_index(mdl_raw, '<INV_VARS>')]
        DiagGMM = [i for i in self.get_index(mdl_raw, '</DiagGMM>')]

        for i in range(total_gmm):
            weight = re.search(
                '\[ (.*) \]', mdl_raw[WEIGHTS[i]]).group(1).split()
            weight = np.array([float(i) for i in weight])
            means_invvars = mdl_raw[MEANS_INVVARS[i]:(INV_VARS[i] - 1)]
            invvars = mdl_raw[INV_VARS[i]:DiagGMM[i]]
            mean = np.zeros((len(invvars), dim))
            var = np.zeros((len(invvars), dim))
            for idx, (mi, iv) in enumerate(zip(means_invvars, invvars)):
                mi, iv = re.sub(r'\]|\[', '', mi), re.sub(r'\]|\[', '', iv)
                var[idx, :] = np.array([1 / float(i) for i in iv.split()])
                mean[idx, :] = np.array([float(i) for i in mi.split()])
            mean = np.multiply(mean, var)
            self.gmm[i] = {'num_gmm': len(
                weight), 'weight': weight, 'mean': mean, 'var': var}

        # Save HMM-GMM info
        self.hmm = {}
        self.pdf = {}
        beg = self.get_index(mdl_raw, '</ForPhones>')
        end = self.get_index(mdl_raw, '</TopologyEntry>')
        nsil_states = [i for i in range(end[0] - beg[0] - 1)]  # e.g. 3
        sil_states = [i for i in range(end[1] - beg[1] - 1)]  # e.g. 5
        ts_idxs = self.get_index(
            self.trans_raw, 'Transition-state') + [len(self.trans_raw)]

        # for nonsilence phones
        n_state = len(nsil_states)
        for ph in self.nonsil_phones:  # loop through phones
            self.hmm[ph] = {'states': '',
                            'trans_prob': '',
                            'self_loop_prob': '',
                            'gmm_id': ''}
            self.hmm[ph]['states'] = nsil_states  # add states
            ph_idxs_beg = self.get_index(
                self.trans_raw, 'phone = {:s}'.format(ph))
            last_idx = ts_idxs.index(ph_idxs_beg[-1])
            ph_idxs_end = ph_idxs_beg[1:] + [ts_idxs[last_idx + 1]]
            self_loop_prob = []
            gmm_id = []
            trans_matrix = np.zeros((n_state, n_state))
            for i, (beg, end) in enumerate(zip(ph_idxs_beg, ph_idxs_end)):  # loop through phone states
                pdf_id = re.search('pdf = (.*)', self.trans_raw[beg]).group(1)
                pdf_id = int(pdf_id.split()[0])
                state_id = re.search(
                    'hmm\-state = (.*) pdf', self.trans_raw[beg]).group(1)
                state_id = int(state_id.split()[0])
                gmm_id.append(pdf_id)
                trans_tmp = self.trans_raw[(beg + 1):(end)]
                for line in trans_tmp:  # loop through each line in phone state
                    if re.search('self-loop', line):
                        self_loop = float(
                            re.search('p = (.*) \[self\-loop\]', line).group(1))
                        self_loop_prob.append(self_loop)
                        trans_matrix[state_id, state_id] = self_loop
                    else:
                        beg_state = int(re.search('\[(.*) \-', line).group(1))
                        end_state = int(re.search('\> (.*)\]', line).group(1))
                        prob = float(re.search('p = (.*) \[', line).group(1))
                        trans_matrix[beg_state, end_state] = prob
            self.hmm[ph]['trans_prob'] = trans_matrix
            self.hmm[ph]['self_loop_prob'] = self_loop_prob
            self.hmm[ph]['gmm_id'] = gmm_id

            # write pdf id for phone
            for i, g in enumerate(gmm_id):
                self.pdf[g] = (ph, i)

        print('  nonsilence phones were succefully loaded')

        # for silence phones
        n_state = len(sil_states)
        for ph in self.sil_phones:  # loop through phones
            self.hmm[ph] = {'states': '',
                            'trans_prob': '',
                            'self_loop_prob': '',
                            'gmm_id': ''}
            self.hmm[ph]['states'] = sil_states  # add states
            ph_idxs_beg = self.get_index(
                self.trans_raw, 'phone = {:s}'.format(ph))
            last_idx = ts_idxs.index(ph_idxs_beg[-1])
            ph_idxs_end = ph_idxs_beg[1:] + [ts_idxs[last_idx + 1]]
            self_loop_prob = []
            gmm_id = []
            trans_matrix = np.zeros((n_state, n_state))
            for i, (beg, end) in enumerate(zip(ph_idxs_beg, ph_idxs_end)):  # loop through phone states
                pdf_id = re.search('pdf = (.*)', self.trans_raw[beg]).group(1)
                pdf_id = int(pdf_id.split()[0])
                state_id = re.search(
                    'hmm\-state = (.*) pdf', self.trans_raw[beg]).group(1)
                state_id = int(state_id.split()[0])
                gmm_id.append(pdf_id)
                trans_tmp = self.trans_raw[(beg + 1):(end)]
                for line in trans_tmp:  # loop through each line in phone state
                    if re.search('self-loop', line):
                        self_loop = float(
                            re.search('p = (.*) \[self\-loop\]', line).group(1))
                        self_loop_prob.append(self_loop)
                        trans_matrix[state_id, state_id] = self_loop
                    else:
                        beg_state = int(re.search('\[(.*) \-', line).group(1))
                        end_state = int(re.search('\> (.*)\]', line).group(1))
                        prob = float(re.search('p = (.*) \[', line).group(1))
                        trans_matrix[beg_state, end_state] = prob
            self.hmm[ph]['trans_prob'] = trans_matrix
            self.hmm[ph]['self_loop_prob'] = self_loop_prob
            self.hmm[ph]['gmm_id'] = gmm_id

            # write pdf id for phone
            for i, g in enumerate(gmm_id):
                self.pdf[g] = (ph, i)  # (phone, num state)

        print('  silence phones were succefully loaded')
        print('{} is loaded'.format(self.mdl_txt))
        return print('''
        ==============================================================
        Now try following:

        >> H.hmm['{0}'].keys() # get each phone info
           dict_keys(['states', 'trans_prob', 'self_loop_prob', 'gmm_id'])
        >> H.hmm['{0}']['gmm_id'] # get gmm id (=pdf id)
           {1}
        >> H.gmm[{2}].keys() # access gmm info
           {3}
        ==============================================================
        '''.format(self.nonsil_phones[0],
                   str(self.hmm[self.nonsil_phones[0]]['gmm_id']),
                   str(self.hmm[self.nonsil_phones[0]]['gmm_id'][0]),
                   str(self.gmm[self.hmm[self.nonsil_phones[0]]['gmm_id'][0]].keys())))

    def get_index(self, target, pattern):
        '''
        target: a list or a string
        pattern: regular expression
        '''
        return [i for i, item in enumerate(target) if re.search(pattern, item)]

    def save_dict(self):
        '''
        Save HMM/GMM dictionary as .pickle file
        TODO: Think about what and how to save
        TODO: Finish save_result()
        '''
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        currTime = strftime("%Y-%m-%d_%H-%M-%S", gmtime())
        fname = os.path.join(self.save_dir, currTime + '_hmm_gmm.pckl')
        with open(fname, 'wb') as pckl:
            HMM = self.hmm
            GMM = self.gmm
            pickle.dump([HMM, GMM], pckl)
            return print('{} saved'.format(fname))

    def draw_hmm(self, phone, save_dir, remove_dot=True):
        '''
        Draw HMM diagram for a phone and save output .pdf under 'save_dir'
        e.g.
        >> H = GetHMM(mdl_txt, trans_txt, phones_txt, sets_txt)
        >> H.draw_hmm('AA_B')
        '''

        # TODO: check 'dot' program exists or not (throw an error)

        P = self.hmm[phone]
        states = P['states'][:-1]  # exclude final non-emitting state
        gmm_id = P['gmm_id']
        num_gmm = [self.gmm[i]['num_gmm']
                   for i in gmm_id]
        gmm_std_on_vars = [
            np.mean(np.std(self.gmm[i]['var'], axis=1)) for i in gmm_id]
        gmm_std_on_means = [
            np.mean(np.std(self.gmm[i]['mean'], axis=1)) for i in gmm_id]
        gmm_mean_on_weights = [
            np.mean(self.gmm[i]['weight']) for i in gmm_id]
        gmm_std_on_weights = [
            np.std(self.gmm[i]['weight']) for i in gmm_id]
        trans_mat = P['trans_prob']

        # Write to a .txt file temporarily
        lines = []
        lines.append('digraph G {')
        lines.append('        ratio=auto;')
        lines.append('        orientation=landscape;')
        lines.append('        center=true;')
        lines.append('        rankdir=LR;')
        for i in range(len(states)):
            lines.append('        s{} [label="s{}"]'.format(i, i))
        lines.append('        {node[shape=record]')
        for i in range(len(states)):
            lines.append(
                '        o{:d} [label="NumGMM:{} | std(means):{:.2f}"]'.format(i, num_gmm[i], gmm_std_on_means[i], gmm_std_on_vars[i], gmm_mean_on_weights[i], gmm_std_on_weights[i]))
        # for i in range(len(states)):
        #     lines.append(
        #         '        o{:d} [label="{:.2f}"]'.format(i, gmm_std_on_means[i]))
        lines.append('        }')
        lines.append('        {node [color=white];')
        lines.append('        title [label="{}",fontsize=30]'.format(phone))
        lines.append('        }')
        lines.append('        {rank=same; s0 o0}')
        lines.append('        {rank=same; title s1 o1}')
        lines.append('        {rank=same; s2 o2}')
        lines.append('        subgraph trans {')
        lines.append(
            '        s0 -> s1 [label="{:.2f}"]'.format(trans_mat[0, 1]))
        lines.append(
            '        s1 -> s2 [label="{:.2f}"]'.format(trans_mat[1, 2]))
        lines.append(
            '        s2 -> s3 [label="{:.2f}"]'.format(trans_mat[2, 3]))
        lines.append('        }')
        lines.append('        subgraph selfloop {')
        lines.append(
            '        s0 -> s0 [label="{:.2f}"]'.format(trans_mat[0, 0]))
        lines.append(
            '        s1 -> s1 [label="{:.2f}"]'.format(trans_mat[1, 1]))
        lines.append(
            '        s2 -> s2 [label="{:.2f}"]'.format(trans_mat[2, 2]))
        lines.append('        }')
        lines.append('        subgraph obs {')
        lines.append('        s0 -> o0')
        lines.append('        s1 -> o1')
        lines.append('        s2 -> o2')
        lines.append('        }')

        lines.append('}')

        tmp_name = os.path.join(save_dir, phone + '.dot')
        new_name = os.path.join(save_dir, phone + '.pdf')
        with open(tmp_name, 'w') as f:
            for i in lines:
                f.write(i + '\n')
        cmd = 'dot -Tps {} | ps2pdf - {}'.format(tmp_name, new_name)
        os.system(cmd)
        if remove_dot:
            os.remove(tmp_name, dir_fd=None)


if __name__ == '__main__':

    mdl_txt = 'data/final.txt'
    trans_txt = 'data/trans_prob.txt'
    phones_txt = 'data/phones.txt'
    sets_txt = 'data/sets.txt'
    save_dir = 'result'

    H = GetParam(mdl_txt, trans_txt, phones_txt, sets_txt, save_dir)
    H.save_dict()  # save HMM, GMM parameters as .pickle file

    # H.draw_hmm('AA_B', H.save_dir)

    # # Draw unique GMMs (e.g. 41 sets from sets.txt)
    # for i, iset in enumerate(H.sets_raw):
    #     dir_name = os.path.join('../result/stdmeans', 'set{}'.format(i + 1))
    #     if not os.path.exists(dir_name):
    #         os.mkdir(dir_name)
    #     for ph in iset:
    #         H.draw_hmm(ph, dir_name)

    # # Draw unique GMMs (one per each set)
    # for i, iset in enumerate(H.sets_raw):
    #     dir_name = os.path.join(
    #         '../result/stdmeans_sample_cal_right', 'set{}'.format(i + 1))
    #     if not os.path.exists(dir_name):
    #         os.mkdir(dir_name)
    #     H.draw_hmm(iset[0], dir_name, remove_dot=False)

    # # Draw unique GMMs (e.g. 41 sets from sets.txt)
    # for i, iset in enumerate(H.sets_raw):
    #     dir_name = os.path.join(
    #         '../result/stdmeans_numgmm', 'set{}'.format(i + 1))
    #     if not os.path.exists(dir_name):
    #         os.mkdir(dir_name)
    #     for ph in iset:
    #         H.draw_hmm(ph, dir_name, remove_dot=True)
