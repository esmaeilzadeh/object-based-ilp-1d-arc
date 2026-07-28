max_vars(8).
max_body(8).
max_clauses(3).
:- not body_var(_,1).
:- not body_var(_,2).
non_datalog.

head_pred(out_block,4).
body_pred(block,4).
body_pred(empty_block,3).
body_pred(block_len,3).
body_pred(obj_index,3).
body_pred(left_of,3).
body_pred(adjacent,3).
body_pred(gap,4).
body_pred(touches_edge,3).
body_pred(block_succ,3).
body_pred(obj_succ,3).
body_pred(shorter,3).
body_pred(longer,3).
body_pred(same_len,3).
body_pred(largest,2).
body_pred(smallest,2).
body_pred(non_largest,2).
body_pred(empty_block_count,2).
body_pred(unique_color,2).
body_pred(offset_pos,3).
body_pred(size_add,3).
body_pred(block_start,3).
body_pred(block_end,3).
body_pred(C,1):- constant(C,_).

constant(s1, size).
constant(left, edge).
constant(right, edge).

type(out_block,('ex', 'position', 'size', 'value')).
type(block,('ex', 'block_id', 'size', 'value')).
type(empty_block,('ex', 'block_id', 'size')).
type(block_len,('ex', 'block_id', 'size')).
type(obj_index,('ex', 'block_id', 'rank')).
type(left_of,('ex', 'block_id', 'block_id')).
type(adjacent,('ex', 'block_id', 'block_id')).
type(gap,('ex', 'block_id', 'block_id', 'size')).
type(touches_edge,('ex', 'block_id', 'edge')).
type(block_succ,('ex', 'block_id', 'block_id')).
type(obj_succ,('ex', 'block_id', 'block_id')).
type(shorter,('ex', 'block_id', 'block_id')).
type(longer,('ex', 'block_id', 'block_id')).
type(same_len,('ex', 'block_id', 'block_id')).
type(largest,('ex', 'block_id')).
type(smallest,('ex', 'block_id')).
type(non_largest,('ex', 'block_id')).
type(empty_block_count,('ex', 'size')).
type(unique_color,('ex', 'value')).
type(offset_pos,('position', 'size', 'position')).
type(size_add,('size', 'size', 'size')).
type(block_start,('ex', 'block_id', 'position')).
type(block_end,('ex', 'block_id', 'position')).
type(C,(T,)):- constant(C,T).

bad_body(block, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(empty_block, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(block_len, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(obj_index, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(left_of, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(adjacent, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(gap, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(touches_edge, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(block_succ, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(obj_succ, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(shorter, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(longer, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(same_len, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(largest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(smallest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(non_largest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(empty_block_count, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(unique_color, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(block_start, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(block_end, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.

