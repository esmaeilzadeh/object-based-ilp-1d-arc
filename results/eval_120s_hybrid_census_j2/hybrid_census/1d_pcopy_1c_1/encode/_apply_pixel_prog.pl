:- dynamic out/3.
out(V0,V1,V2):- in(V0,V1,V2).
out(V0,V1,V2):- c6(V3),my_succ(V5,V1),in(V0,V5,V2),add(V3,V4,V1).
out(V0,V1,V2):- my_succ(V1,V5),in(V0,V5,V2),in(V0,V4,V2),add(V3,V4,V1).
