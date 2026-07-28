max_vars(8).
max_body(8).
max_clauses(3).
:- not body_var(_,1).
:- not body_var(_,2).
non_datalog.

head_pred(out_block,4).
body_pred(block,4).
body_pred(block_len,3).
body_pred(block_start,3).
body_pred(block_end,3).
body_pred(marker_block,2).
body_pred(unit_block,2).
body_pred(reflect_pos,4).
body_pred(reflect_end,4).
body_pred(block_marker_gap,4).
body_pred(offset_pos,3).
body_pred(size_add,3).
body_pred(C,1):- constant(C,_).

constant(s1, size).

type(out_block,('ex', 'position', 'size', 'value')).
type(block,('ex', 'block_id', 'size', 'value')).
type(block_len,('ex', 'block_id', 'size')).
type(block_start,('ex', 'block_id', 'position')).
type(block_end,('ex', 'block_id', 'position')).
type(marker_block,('ex', 'block_id')).
type(unit_block,('ex', 'block_id')).
type(reflect_pos,('ex', 'position', 'position', 'position')).
type(reflect_end,('ex', 'block_id', 'block_id', 'position')).
type(block_marker_gap,('ex', 'block_id', 'block_id', 'size')).
type(offset_pos,('position', 'size', 'position')).
type(size_add,('size', 'size', 'size')).
type(C,(T,)):- constant(C,T).

bad_body(block, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(block_len, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(block_start, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(block_end, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(marker_block, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(unit_block, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(reflect_pos, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(reflect_end, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(block_marker_gap, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.

