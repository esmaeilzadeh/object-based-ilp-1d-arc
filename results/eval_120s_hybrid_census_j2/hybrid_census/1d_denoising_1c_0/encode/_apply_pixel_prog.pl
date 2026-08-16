:- dynamic out/3.
out(V0,V1,V2):- in(V0,V4,V2),add(V4,V6,V1),my_succ(V4,V5),in(V0,V5,V2),add(V1,V3,V5).
