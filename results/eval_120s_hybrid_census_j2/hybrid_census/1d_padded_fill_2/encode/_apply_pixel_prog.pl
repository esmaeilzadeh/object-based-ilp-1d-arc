:- dynamic out/3.
out(V0,V1,V2):- c8(V5),add(V4,V5,V1),in(V0,V4,V2),add(V3,V4,V5).
out(V0,V1,V2):- my_succ(V1,V5),in(V0,V5,V2),my_succ(V4,V3),add(V3,V4,V1).
out(V0,V1,V2):- c9(V1),in(V0,V3,V2),add(V3,V4,V1).
out(V0,V1,V2):- c4(V1),in(V0,V3,V2),add(V3,V4,V1).
out(V0,V1,V2):- c6(V5),add(V4,V5,V1),in(V0,V4,V2),add(V3,V4,V5).
out(V0,V1,V2):- in(V0,V1,V2).
out(V0,V1,V2):- my_succ(V4,V1),my_succ(V1,V5),in(V0,V5,V2),in(V0,V4,V3).
out(V0,V1,V2):- c6(V1),in(V0,V3,V2),add(V3,V4,V1).
out(V0,V1,V2):- c8(V1),in(V0,V3,V2),add(V3,V4,V1).
out(V0,V1,V2):- c9(V5),add(V4,V5,V1),in(V0,V4,V2),add(V3,V4,V5).
out(V0,V1,V2):- c5(V1),in(V0,V3,V2),add(V3,V4,V1).
out(V0,V1,V2):- c7(V1),in(V0,V3,V2),add(V3,V4,V1).
out(V0,V1,V2):- c9(V3),my_succ(V3,V1),in(V0,V5,V2),add(V4,V5,V1).
out(V0,V1,V2):- c7(V5),add(V4,V5,V1),in(V0,V4,V2),add(V3,V4,V5).
