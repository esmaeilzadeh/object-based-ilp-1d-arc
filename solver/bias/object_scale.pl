max_vars(9).
max_body(6).
max_clauses(2).
enable_multi_clause.

head_pred(out_block,5).
body_pred(block,4).
body_pred(gap,4).
body_pred(obj_succ,3).
body_pred(largest,2).
body_pred(non_largest,2).
body_pred(size_add,3).
body_pred(C,1):- constant(C,_).

constant(s0, 'size').
constant(s1, 'size').

type(out_block,('ex', 'block_id', 'size', 'size', 'value')).
type(block,('ex', 'block_id', 'size', 'value')).
type(gap,('ex', 'block_id', 'block_id', 'size')).
type(obj_succ,('ex', 'block_id', 'block_id')).
type(largest,('ex', 'block_id')).
type(non_largest,('ex', 'block_id')).
type(size_add,('size', 'size', 'size')).
type(C,(T,)):- constant(C,T).

bad_body(block, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(gap, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(obj_succ, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(largest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(non_largest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.

