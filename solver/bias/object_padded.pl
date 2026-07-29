max_vars(9).
max_body(6).
max_clauses(1).
:- not body_var(_,1).
:- not body_var(_,2).
:- not body_var(_,3).

head_pred(out_block,5).
body_pred(block,4).
body_pred(gap,4).
body_pred(size_sum3,4).
body_pred(obj_pair,3).
body_pred(C,1):- constant(C,_).

constant(s0, 'size').
constant(s1, 'size').

type(out_block,('ex', 'block_id', 'size', 'size', 'value')).
type(block,('ex', 'block_id', 'size', 'value')).
type(gap,('ex', 'block_id', 'block_id', 'size')).
type(size_sum3,('size', 'size', 'size', 'size')).
type(obj_pair,('ex', 'block_id', 'block_id')).
type(C,(T,)):- constant(C,T).

bad_body(block, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(gap, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(obj_pair, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.

