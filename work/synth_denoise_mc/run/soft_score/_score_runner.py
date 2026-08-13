import json, sys
from janus_swi import consult, query_once
do_test = '/home/mohamad/Projects/UNI/machine learning/ml-project/object-based-ilp-1d-arc/solver/lp/do_test.pl'
test_path = 'work/synth_denoise_mc/run/encode/test.pl'
prog_file = 'work/synth_denoise_mc/run/soft_score/_score_prog.pl'
try:
    consult(do_test)
    consult(test_path)
    consult(prog_file)
    res = query_once('do_test_ex(TP,FN,TN,FP)')
    matrix = [int(res['TP']), int(res['FN']), int(res['TN']), int(res['FP'])]
except Exception:
    try:
        consult(do_test)
        consult(test_path)
        num_pos = int(query_once('num_pos(P)')['P'])
        num_neg = int(query_once('num_neg(N)')['N'])
        matrix = [0, num_pos, num_neg, 0]
    except Exception:
        matrix = [0, 1, 0, 0]
tp, fn, tn, fp = matrix
total = tp + fn + tn + fp
acc = (tp + tn) / total if total else 0.0
print(json.dumps({'matrix': matrix, 'acc': acc}))
