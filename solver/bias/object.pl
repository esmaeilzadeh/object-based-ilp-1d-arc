max_vars(8).
max_body(6).
non_datalog.

head_pred(out_block,4).
body_pred(block,4).
body_pred(obj_succ,3).
body_pred(smallest,2).
body_pred(block_start,3).
body_pred(after_block,3).
body_pred(C,1):- constant(C,_).


type(out_block,('ex', 'position', 'size', 'value')).
type(block,('ex', 'block_id', 'size', 'value')).
type(obj_succ,('ex', 'block_id', 'block_id')).
type(smallest,('ex', 'block_id')).
type(block_start,('ex', 'block_id', 'position')).
type(after_block,('ex', 'block_id', 'position')).
type(C,(T,)):- constant(C,T).

bad_body(block, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(obj_succ, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(smallest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(block_start, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(after_block, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.

