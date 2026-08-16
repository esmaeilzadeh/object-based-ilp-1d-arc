:- dynamic out/3.
out(V0,V1,V2):- my_succ(V3,V1),in(V0,V3,V2),c7(V5),add(V4,V5,V1).
out(V0,V1,V2):- my_succ(V1,V3),in(V0,V3,V2),c3(V4),add(V4,V5,V1).
out(V0,V1,V2):- in(V0,V1,V2).
