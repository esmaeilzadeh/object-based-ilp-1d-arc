max_vars(10).
max_body(6).
max_clauses(3).
enable_multi_clause.
functional.
:- not body_var(_,1).
:- not body_var(_,2).
:- not body_var(_,3).

head_pred(out_block,4).
body_pred(block,4).
body_pred(largest,2).
body_pred(succ,2).
body_pred(add,3).
body_pred(size_lt,2).
body_pred(C,1):- constant(C,_).

constant(n0, 'num').
constant(n1, 'num').
constant(n2, 'num').
constant(n3, 'num').
constant(n8, 'num').
constant(n9, 'num').
constant(n10, 'num').
constant(n11, 'num').

type(out_block,('ex','num','num','value')).
type(block,('ex','num','num','value')).
type(largest,('ex','num')).
type(succ,('num','num')).
type(add,('num','num','num')).
type(size_lt,('num','num')).
type(C,(T,)):- constant(C,T).

:- clause(C), not body_literal(C, block, 4, (0,_,_,_)).
:- clause(C), not body_literal(C, block, 4, (0,1,_,_)), not body_literal(C, succ, 2, (1,_)), not body_literal(C, succ, 2, (_,1)), not body_literal(C, add, 3, (1,_,_)), not body_literal(C, add, 3, (_,_,1)).
:- clause(C), body_literal(C, succ, 2, V1), body_literal(C, succ, 2, V2), V1 != V2.
:- clause(C), body_literal(C, add, 3, V1), body_literal(C, add, 3, V2), V1 != V2.
:- clause(C), body_literal(C, succ, 2, _), body_literal(C, add, 3, _).
bad_body(add, Vars):- vars(_, Vars), Vars = (A,B,R), A != 1, B != 1, R != 1, A != 2, B != 2, R != 2.
bad_body(succ, Vars):- vars(_, Vars), Vars = (A,R), A != 1, R != 1, A != 2, R != 2.

