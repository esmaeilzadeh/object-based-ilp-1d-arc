% Paper-style soft scoring (from ijcai25-relational-decomposition / 1d-arc test.pl).
% Counts each pos/neg out label (not per example id).
:- dynamic pos/1.
:- dynamic neg/1.
:- dynamic out/2.
:- dynamic out/3.
:- dynamic out/4.
:- dynamic empty/3.
:- dynamic in/4.
:- dynamic different/2.
:- style_check(-singleton).

do_test_ex(TP, FN, TN, FP) :-
    findall(Atom, pos_atom(Atom), PosAtoms),
    findall(Atom, neg_atom(Atom), NegAtoms),
    score_pos(PosAtoms, 0, 0, TP, FN),
    score_neg(NegAtoms, 0, 0, TN, FP).

pos_atom(Atom) :-
    current_predicate(pos/1),
    pos(Atom).

neg_atom(Atom) :-
    current_predicate(neg/1),
    neg(Atom).

score_pos([], TP, FN, TP, FN).
score_pos([A|As], TP0, FN0, TP, FN) :-
    (test_ex(A) ->
        TP1 is TP0 + 1, FN1 = FN0
    ;
        TP1 = TP0, FN1 is FN0 + 1
    ),
    score_pos(As, TP1, FN1, TP, FN).

score_neg([], TN, FP, TN, FP).
score_neg([A|As], TN0, FP0, TN, FP) :-
    (test_ex(A) ->
        FP1 is FP0 + 1, TN1 = TN0
    ;
        TN1 is TN0 + 1, FP1 = FP0
    ),
    score_neg(As, TN1, FP1, TN, FP).

test_ex(X) :-
    timeout(T),
    catch(call_with_time_limit(T, call(X)), time_limit_exceeded, false), !.

timeout(1).

num_pos(P) :-
    (current_predicate(pos/1) -> findall(X, pos(X), Xs), length(Xs, P) ; P = 0).
num_neg(N) :-
    (current_predicate(neg/1) -> findall(X, neg(X), Xs), length(Xs, N) ; N = 0).
