# -*- coding: utf-8 -*-
"""Servicios todavía sin cliente real (mismo estado que en el móvil).

File Sync (gRPC, node-sync:9090)
    El servidor y su `.proto` existen (node-sync/proto/filesync/filesync.proto),
    pero falta generar el stub de Python (`grpcio-tools`). Ojo al hacerlo: el
    servidor IGNORA los campos `uid` y saca el usuario del token, que viaja
    como metadata `authorization: Bearer <token>`. Mientras tanto, la vista de
    sincronización trabaja en local (detecta cambios en la carpeta elegida).

HPC (RMI -> SLURM/MPI)
    El contrato exige RMI, que solo existe en la JVM. Ni Python ni Android lo
    tienen. Decisión pendiente con Dev C: (a) que HPC exponga también
    gRPC/REST para clientes no-JVM, o (b) dejar el envío de trabajos fuera de
    los clientes en esta versión. Mientras tanto, los trabajos se encolan en
    local (demo).
"""

FILESYNC_DISPONIBLE = False
HPC_DISPONIBLE = False
