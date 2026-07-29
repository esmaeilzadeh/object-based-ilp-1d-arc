max_vars(8).
max_body(3).
max_clauses(1).
:- not body_var(_,1).
:- not body_var(_,2).

head_pred(out_block,4).
body_pred(block,4).
body_pred(largest,2).

type(out_block,('ex', 'block_id', 'size', 'value')).
type(block,('ex', 'block_id', 'size', 'value')).
type(largest,('ex', 'block_id')).

bad_body(block, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(largest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.

