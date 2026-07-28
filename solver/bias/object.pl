max_vars(12).
max_body(8).
max_clauses(2).
:- not body_var(_,1).
:- not body_var(_,2).
non_datalog.

head_pred(out_block,4).
body_pred(block,4).
body_pred(empty_block,3).
body_pred(block_len,3).
body_pred(left_of,3).
body_pred(adjacent,3).
body_pred(gap,4).
body_pred(block_succ,3).
body_pred(obj_succ,3).
body_pred(largest,2).
body_pred(size_add,3).
body_pred(C,1):- constant(C,_).

constant(s1, size).
constant(left, edge).
constant(right, edge).

type(out_block,('ex', 'block_id', 'size', 'value')).
type(block,('ex', 'block_id', 'size', 'value')).
type(empty_block,('ex', 'block_id', 'size')).
type(block_len,('ex', 'block_id', 'size')).
type(left_of,('ex', 'block_id', 'block_id')).
type(adjacent,('ex', 'block_id', 'block_id')).
type(gap,('ex', 'block_id', 'block_id', 'size')).
type(block_succ,('ex', 'block_id', 'block_id')).
type(obj_succ,('ex', 'block_id', 'block_id')).
type(largest,('ex', 'block_id')).
type(size_add,('size', 'size', 'size')).
type(C,(T,)):- constant(C,T).

bad_body(block, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(empty_block, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(block_len, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(left_of, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(adjacent, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(gap, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(block_succ, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(obj_succ, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(largest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.

