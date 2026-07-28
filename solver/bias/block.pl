max_vars(8).
max_body(12).
non_datalog.

head_pred(out,3).
body_pred(block,4).
body_pred(empty_block,3).
body_pred(obj_index,3).
body_pred(left_of,3).
body_pred(adjacent,3).
body_pred(touches_edge,3).
body_pred(block_succ,3).
body_pred(shorter,3).
body_pred(longer,3).
body_pred(same_len,3).
body_pred(largest,2).
body_pred(smallest,2).
body_pred(non_largest,2).
body_pred(empty_block_count,2).
body_pred(unique_color,2).
body_pred(pixel_block,3).
body_pred(in_block,3).
body_pred(block_edge,3).
body_pred(in_gap,4).
body_pred(block_cell,4).
body_pred(edge_cell,4).
body_pred(interior_cell,4).
body_pred(solid_cell,4).
body_pred(gap_cell,5).
body_pred(marker_block,2).
body_pred(reflect_pos,4).
body_pred(reflect_end,4).
body_pred(between_block_marker,4).
body_pred(block_marker_gap,4).
body_pred(same_side_marker,3).
body_pred(opp_side_marker,3).
body_pred(offset_pos,3).
body_pred(size_add,3).
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
constant(left, edge).
constant(right, edge).

type(out,('ex', 'position', 'value')).
type(block,('ex', 'block_id', 'size', 'value')).
type(empty_block,('ex', 'block_id', 'size')).
type(obj_index,('ex', 'block_id', 'rank')).
type(left_of,('ex', 'block_id', 'block_id')).
type(adjacent,('ex', 'block_id', 'block_id')).
type(touches_edge,('ex', 'block_id', 'edge')).
type(block_succ,('ex', 'block_id', 'block_id')).
type(shorter,('ex', 'block_id', 'block_id')).
type(longer,('ex', 'block_id', 'block_id')).
type(same_len,('ex', 'block_id', 'block_id')).
type(largest,('ex', 'block_id')).
type(smallest,('ex', 'block_id')).
type(non_largest,('ex', 'block_id')).
type(empty_block_count,('ex', 'size')).
type(unique_color,('ex', 'value')).
type(pixel_block,('ex', 'position', 'block_id')).
type(in_block,('ex', 'block_id', 'position')).
type(block_edge,('ex', 'block_id', 'position')).
type(in_gap,('ex', 'block_id', 'block_id', 'position')).
type(block_cell,('ex', 'block_id', 'position', 'value')).
type(edge_cell,('ex', 'block_id', 'position', 'value')).
type(interior_cell,('ex', 'block_id', 'position', 'value')).
type(solid_cell,('ex', 'block_id', 'position', 'value')).
type(gap_cell,('ex', 'block_id', 'block_id', 'position', 'value')).
type(marker_block,('ex', 'block_id')).
type(reflect_pos,('ex', 'position', 'position', 'position')).
type(reflect_end,('ex', 'block_id', 'block_id', 'position')).
type(between_block_marker,('ex', 'block_id', 'block_id', 'position')).
type(block_marker_gap,('ex', 'block_id', 'block_id', 'size')).
type(same_side_marker,('ex', 'block_id', 'block_id')).
type(opp_side_marker,('ex', 'block_id', 'block_id')).
type(offset_pos,('position', 'size', 'position')).
type(size_add,('size', 'size', 'size')).
type(C,(T,)):- constant(C,T).

bad_body(block, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(empty_block, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(obj_index, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(left_of, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(adjacent, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(touches_edge, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(block_succ, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(shorter, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(longer, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(same_len, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(largest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(smallest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(non_largest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(empty_block_count, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(unique_color, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(pixel_block, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(in_block, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(block_edge, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(in_gap, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(block_cell, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(edge_cell, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(interior_cell, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(solid_cell, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(gap_cell, Vars):- vars(_, Vars), Vars = (V0,_,_,_,_), V0 != 0.
bad_body(marker_block, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(reflect_pos, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(reflect_end, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(between_block_marker, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(block_marker_gap, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(same_side_marker, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(opp_side_marker, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.

