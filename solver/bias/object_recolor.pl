max_vars(8).
max_body(6).
max_clauses(2).

head_pred(out_block,4).
body_pred(block,4).
body_pred(largest,2).
body_pred(non_largest,2).
body_pred(size_even,1).
body_pred(size_odd,1).
body_pred(C,1):- constant(C,_).

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

type(out_block,('ex', 'block_id', 'size', 'value')).
type(block,('ex', 'block_id', 'size', 'value')).
type(largest,('ex', 'block_id')).
type(non_largest,('ex', 'block_id')).
type(size_even,('size',)).
type(size_odd,('size',)).
type(C,(T,)):- constant(C,T).

bad_body(block, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(largest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(non_largest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.

