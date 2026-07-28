% Paper-style soft scoring (from ijcai25-relational-decomposition / 1d-arc test.pl).
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
    find_ids(Ids),
    test_all(Ids, TP, FN, TN, FP).

find_ids(Ids) :-
    find_ids_pos(Xs1),
    find_ids_neg(Xs2),
    append(Xs1, Xs2, All),
    sort(All, Ids).

find_ids_pos([]) :-
    \+ current_predicate(pos/1), !.
find_ids_pos(Xs1) :-
    findall(X, (pos(Atom), Atom =.. [_P|Args], head(Args, X)), Xs1).
find_ids_neg([]) :-
    \+ current_predicate(neg/1), !.
find_ids_neg(Xs1) :-
    findall(X, (neg(Atom), Atom =.. [_P|Args], head(Args, X)), Xs1).

head([H|_], H).

test_all([], 0, 0, 0, 0).
test_all([I|Ids], TP, FN1, TN, FP) :-
    not_test_id(I), !,
    test_all(Ids, TP, FN, TN, FP),
    FN1 is FN + 1.
test_all([_|Ids], TP1, FN, TN, FP) :-
    test_all(Ids, TP, FN, TN, FP),
    TP1 is TP + 1.

not_test_id(I) :-
    current_predicate(pos/1),
    pos(Atom),
    Atom =.. [P|Args],
    length(Args, A),
    \+ current_predicate(P/A), !.
not_test_id(I) :-
    current_predicate(pos/1),
    pos(Atom),
    Atom =.. [_|Args],
    head(Args, I),
    \+ test_ex(Atom).
not_test_id(I) :-
    current_predicate(neg/1),
    neg(Atom),
    Atom =.. [_|Args],
    head(Args, I),
    test_ex(Atom).

test_ex(X) :-
    timeout(T),
    catch(call_with_time_limit(T, call(X)), time_limit_exceeded, false), !.

timeout(1).

num_pos(P) :-
    (current_predicate(pos/1) -> findall(X, pos(X), Xs), length(Xs, P) ; P = 0).
num_neg(N) :-
    (current_predicate(neg/1) -> findall(X, neg(X), Xs), length(Xs, N) ; N = 0).
