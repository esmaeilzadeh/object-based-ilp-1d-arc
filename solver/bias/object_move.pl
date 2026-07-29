max_vars(6).
max_body(3).
max_clauses(1).
:- not body_var(_,1).
:- not body_var(_,2).
:- not body_var(_,3).

head_pred(out_block,5).
body_pred(block,4).
body_pred(C,1):- constant(C,_).

constant(s0, 'size').
constant(s1, 'size').
constant(s2, 'size').
constant(s3, 'size').

type(out_block,('ex', 'block_id', 'size', 'size', 'value')).
type(block,('ex', 'block_id', 'size', 'value')).
type(C,(T,)):- constant(C,T).

bad_body(block, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.

