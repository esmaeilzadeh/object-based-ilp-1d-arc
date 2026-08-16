out(V0,V1,V2):- in(V0,V1,V2),my_succ(V3,V1),in(V0,V3,V4).
out(V0,V1,V2):- in(V0,V1,V2),my_succ(V1,V3),in(V0,V3,V4).
