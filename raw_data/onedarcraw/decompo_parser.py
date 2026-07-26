import clingo
import clingo.script

TEST_PROG1 = """

a:-
    pos(Atom),
    \+ call(Atom),
    writeln(Atom),
    writeln('bad_pos'),!.
a.
b:-
    neg(Atom),
    call(Atom),
    writeln(Atom),
    writeln('bad_neg'),!.
b.
:-
    a, b, halt.
"""

TEST_PROG = """

#show out/3.
#show bad_pos/1.
#show bad_neg/1.
bad_pos((out(A,B,C))):-
    pos(out(A,B,C)),
    not out(A,B,C).

bad_neg((out(A,B,C))):-
    neg(out(A,B,C)),
    out(A,B,C).

"""

NEG_GEN = """
neg(out(A,B,C)):-
    example(A),
    position(B),
    value_(C),
    not pos(out(A,B,C)).

value_(A):-value(A).
% value_(end).

position(0..32).
value(0..9).
"""


BK = """
x0(0).
x1(1).
x2(2).
x3(3).
x4(4).
x5(5).
x6(6).
x7(7).
x8(8).
x9(9).
x10(10).
x11(11).
x12(12).
x13(13).
x14(14).
x15(15).
x16(16).
x17(17).
x18(18).
x19(19).
x20(20).
x21(21).
x22(22).
x23(23).
x24(24).
x25(25).
x26(26).
x27(27).
x28(28).
x29(29).
x30(30).
x31(31).
x32(32).

v0(0).
v1(1).
v2(2).
v3(3).
v4(4).
v5(5).
v6(6).
v7(7).
v8(8).
v9(9).

c0(0).
c1(1).
c2(2).
c3(3).
c4(4).
c5(5).
c6(6).
c7(7).
c8(8).
c9(9).

end(end).

end_position(E,X):-
    in(E,X,end).
not_end_position(E,X):-
    in(E,X,V),
    V != end.

different_pos(A,B):-
    position(A),
    position(B),
    A != B.

different_value(A,B):-
    value(A),
    value(B),
    A != B.

value(0..9).
position(0..V):- max_position(V).
not_end(A):- position(A).
my_succ(A,B):- position(A), position(B), B=A+1.
lt(A,B):- position(A), position(B), A<B.
add(A,B,C):- position(A), position(B), position(C), C=A+B.
"""

BIAS = """
max_vars(7).
max_body(20).

non_datalog.

:- not body_var(_,1).
:- not body_var(_,2).


head_pred(out,3).
body_pred(in,3).
body_pred(my_succ,2).
body_pred(add,3).
body_pred(lt,2).
body_pred(empty,2).
body_pred(C,1):-constant(C,_).

pred_task_specific(in).
pred_task_specific(empty).

constant(v0, value).
constant(v1, value).
constant(v2, value).
constant(v3, value).
constant(v4, value).
constant(v5, value).
constant(v6, value).
constant(v7, value).
constant(v8, value).
constant(v9, value).

constant(c0, position).
constant(c1, position).
constant(c2, position).
constant(c3, position).
constant(c4, position).
constant(c5, position).
constant(c6, position).
constant(c7, position).
constant(c8, position).
constant(c9, position).

type(empty,(ex,position)).
type(out,(ex,position,value)).
type(in,(ex,position,value)).
type(my_succ,(position,position)).
type(add,(position,position,position)).
type(lt,(position,position)).
type(C,(T,)):- constant(C,T).

%% %% BECAUSE WE DO NOT LEARN FROM INTERPRETATIONS
bad_body(in, Vars):-
    vars(_, Vars),
    Vars = (V0,_,_),
    V0 != 0.

bad_body(empty, Vars):-
    vars(_, Vars),
    Vars = (V0,_),
    V0 != 0.
"""

import json
def json2csv(mypath, file, trial, train=True):
    jsonFile = f'{mypath}/{file}/{file}_{trial}.json'
    with open(jsonFile, 'r') as fd:
        obj = json.load(fd)
    if train:
        records = [(datum["input"],datum["output"]) for datum in obj["train"]]
    else:
        records = [(datum["input"],datum["output"]) for datum in obj["test"]]
    exs = []
    gen_exs = []
    bk = []
    examples_id = set()
    for ex, (ex_in, ex_out) in enumerate(records):
        examples_id.add(ex)
        ex_in = ex_in[0]
        ex_out = ex_out[0]
        max_i = 0
        for i, x in enumerate(ex_in):
            if x == 0:
                line = f'empty({ex},{i}).'
            else:
                line = f'in({ex},{i},{x}).'
            bk.append(line)
            max_i = i
        # line = f'in({ex},{max_i+1},end).'
        line = f'max_position({max_i+1}).'
        
        bk.append(line)

        for i, x in enumerate(ex_out):
            line = f'pos(out({ex},{i},{x})).'
            gen_exs.append(line)
            if x != 0:
                # print(x, type(x))
                exs.append(line)
            max_i = i

    bk = '\n'.join(bk) + '\n'

    # print(bk + BK)
    out_bk = ''
    solver = clingo.Control(['-Wnone'])
    solver.add('base', [], bk + BK)
    solver.ground([('base', [])])
    for x in solver.solve(yield_ = True):
        out_bk += '\n' + '.\n'.join(str(x).split(' ')) + '\n'
        # for atom in x.symbols():
            # print(atom)
    # return

    out_bk += '.\n'

    exs = '\n'.join(exs) + '\n'
    gen_exs = '\n'.join(gen_exs) + '\n'
    encoding = NEG_GEN
    for ex in examples_id:
        encoding += f'example({ex}).\n'
    encoding += gen_exs


    solver = clingo.Control(['-Wnone'])
    solver.add('base', [], encoding)
    solver.ground([('base', [])])

    for x in solver.symbolic_atoms.by_signature('neg', arity=1):
        xs = x.symbol.arguments[0].arguments
        ex = xs[0].number
        idx = xs[1].number
        try:
            val = xs[2].number
        except:
            val = xs[2].name
        line = f'neg(out({ex},{idx},{val})).\n'
        exs += line


    import os
    concept = jsonFile.split('/')[-1].split('.')[0]

    path = f'train/relational/1d/{file}/{trial}/'
    import pathlib
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)

    if train:
        with open(path + '/exs.pl', 'w') as f:
            f.write(exs)
        with open(path + '/bk.pl', 'w') as f:
            f.write(out_bk)
        with open(path + '/bias.pl', 'w') as f:
            f.write(BIAS)

    else:
        with open(path + '/test.pl', 'w') as f:
            f.write(exs + '\n')
            f.write(out_bk + '\n')
            # f.write(TEST_PROG)




import sys
import os

def parse1d(max_trial=None):
    """Parse 1D-ARC JSON into train/relational/1d/{task}/{trial}/.

    max_trial: inclusive upper bound (default from env PARSE_MAX_TRIAL or 2).
    Set PARSE_MAX_TRIAL=49 to regenerate all 50 instances.
    """
    if max_trial is None:
        max_trial = int(os.environ.get("PARSE_MAX_TRIAL", "2"))
    script_dir = os.path.dirname(os.path.abspath(__file__))
    mypath = os.path.join(script_dir, "./dataset")
    for file in sorted(os.listdir(mypath)):
        if not os.path.isdir(os.path.join(mypath, file)):
            continue
        print(file)
        for trial in range(0, max_trial + 1):
            json2csv(mypath, file, trial, train=True)
            json2csv(mypath, file, trial, train=False)
