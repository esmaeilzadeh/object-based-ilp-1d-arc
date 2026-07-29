max_vars(8).
max_body(5).
max_clauses(1).
:- not body_var(_,1).
:- not body_var(_,2).
:- not body_var(_,3).

head_pred(out_block,5).
body_pred(block,4).
body_pred(largest,2).
body_pred(component_start,2).
body_pred(component_len,3).
body_pred(C,1):- constant(C,_).

constant(s0, 'size').
constant(s1, 'size').

type(out_block,('ex', 'block_id', 'size', 'size', 'value')).
type(block,('ex', 'block_id', 'size', 'value')).
type(largest,('ex', 'block_id')).
type(component_start,('ex', 'block_id')).
type(component_len,('ex', 'block_id', 'size')).
type(C,(T,)):- constant(C,T).

bad_body(block, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(largest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(component_start, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(component_len, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.

