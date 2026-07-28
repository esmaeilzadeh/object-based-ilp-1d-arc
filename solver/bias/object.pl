max_vars(8).
max_body(10).
non_datalog.

head_pred(out_block,4).
body_pred(block,4).
body_pred(obj_succ,3).
body_pred(smallest,2).
body_pred(block_start,3).
body_pred(after_block,3).
body_pred(marker_block,2).
body_pred(reflect_pos,4).
body_pred(between_block_marker,4).
body_pred(block_marker_gap,4).
body_pred(same_side_marker,3).
body_pred(opp_side_marker,3).
body_pred(offset_pos,3).
body_pred(C,1):- constant(C,_).


type(out_block,('ex', 'position', 'size', 'value')).
type(block,('ex', 'block_id', 'size', 'value')).
type(obj_succ,('ex', 'block_id', 'block_id')).
type(smallest,('ex', 'block_id')).
type(block_start,('ex', 'block_id', 'position')).
type(after_block,('ex', 'block_id', 'position')).
type(marker_block,('ex', 'block_id')).
type(reflect_pos,('ex', 'position', 'position', 'position')).
type(between_block_marker,('ex', 'block_id', 'block_id', 'position')).
type(block_marker_gap,('ex', 'block_id', 'block_id', 'size')).
type(same_side_marker,('ex', 'block_id', 'block_id')).
type(opp_side_marker,('ex', 'block_id', 'block_id')).
type(offset_pos,('position', 'size', 'position')).
type(C,(T,)):- constant(C,T).

bad_body(block, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(obj_succ, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(smallest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(block_start, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(after_block, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(marker_block, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(reflect_pos, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(between_block_marker, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(block_marker_gap, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(same_side_marker, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(opp_side_marker, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.

