max_vars(6).
max_body(12).
non_datalog.

head_pred(out,3).
body_pred(width,2).
body_pred(block,5).
body_pred(block_len,3).
body_pred(left_of,3).
body_pred(adjacent,3).
body_pred(gap,4).
body_pred(touches_edge,3).
body_pred(largest,2).
body_pred(smallest,2).
body_pred(block_count,2).
body_pred(color_count,3).
body_pred(unique_color,2).
body_pred(len_rank,3).
body_pred(mid,2).
body_pred(mirror_index,3).
body_pred(from_right,3).
body_pred(my_succ,2).
body_pred(lt,2).
body_pred(add,3).
body_pred(span,3).
body_pred(span_shift,4).
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
constant(c0, position).
constant(c1, position).
constant(c2, position).
constant(c3, position).
constant(c4, position).
constant(c5, position).
constant(c6, position).
constant(c7, position).
constant(c8, position).
constant(c9, position).
constant(left, edge).
constant(right, edge).

type(out,('ex', 'position', 'value')).
type(width,('ex', 'position')).
type(block,('ex', 'block_id', 'position', 'position', 'value')).
type(block_len,('ex', 'block_id', 'position')).
type(left_of,('ex', 'block_id', 'block_id')).
type(adjacent,('ex', 'block_id', 'block_id')).
type(gap,('ex', 'block_id', 'block_id', 'position')).
type(touches_edge,('ex', 'block_id', 'edge')).
type(largest,('ex', 'block_id')).
type(smallest,('ex', 'block_id')).
type(block_count,('ex', 'position')).
type(color_count,('ex', 'value', 'position')).
type(unique_color,('ex', 'value')).
type(len_rank,('ex', 'block_id', 'position')).
type(mid,('ex', 'position')).
type(mirror_index,('ex', 'position', 'position')).
type(from_right,('ex', 'position', 'position')).
type(my_succ,('position', 'position')).
type(lt,('position', 'position')).
type(add,('position', 'position', 'position')).
type(span,('position', 'position', 'position')).
type(span_shift,('position', 'position', 'position', 'position')).
type(C,(T,)):- constant(C,T).

bad_body(width, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(block, Vars):- vars(_, Vars), Vars = (V0,_,_,_,_), V0 != 0.
bad_body(block_len, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(left_of, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(adjacent, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(gap, Vars):- vars(_, Vars), Vars = (V0,_,_,_), V0 != 0.
bad_body(touches_edge, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(largest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(smallest, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(block_count, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(color_count, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(unique_color, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(len_rank, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(mid, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(mirror_index, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(from_right, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.

