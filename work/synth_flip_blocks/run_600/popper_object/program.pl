out_block(V0,V1,V2,V3,V4):- block(V0,V1,V5,V4),gap(V0,V6,V1,V7),size_sum3(V3,V7,V2,V8).
out_block(V0,V1,V2,V3,V4):- block(V0,V5,V8,V4),size_add(V8,V2,V3),block(V0,V1,V6,V7),v6(V7).
out_block(V0,V1,V2,V3,V4):- v5(V4),block(V0,V1,V8,V9),size_add(V8,V2,V7),size_sum3(V3,V7,V6,V5).
out_block(V0,V1,V2,V3,V4):- block(V0,V5,V8,V4),gap(V0,V6,V5,V2),block(V0,V1,V3,V7),gap(V0,V1,V6,V9).
out_block(V0,V1,V2,V3,V4):- s4(V2),s3(V3),block(V0,V1,V5,V4).
out_block(V0,V1,V2,V3,V4):- size_even(V2),block(V0,V1,V2,V6),block(V0,V5,V3,V4),gap(V0,V1,V5,V3).
out_block(V0,V1,V2,V3,V4):- v6(V4),size_add(V2,V3,V5),block(V0,V1,V5,V6).
out_block(V0,V1,V2,V3,V4):- v1(V4),gap(V0,V5,V1,V2),block(V0,V1,V3,V6).
