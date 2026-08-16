out(V0,V1,V2):- my_succ(V5,V1),in(V0,V5,V2),c5(V3),add(V3,V4,V5).
out(V0,V1,V2):- my_succ(V1,V6),in(V0,V6,V2),in(V0,V3,V5),add(V3,V4,V1).
out(V0,V1,V2):- in(V0,V1,V2).
