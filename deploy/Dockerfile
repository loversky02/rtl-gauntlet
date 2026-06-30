# Railway CPU worker for C3 PPA data-gen.
# Base = the OpenLane 2 image: Yosys/OpenROAD/Magic/Netgen are already inside it, so
# `openlane config.json` runs NATIVELY here — no Docker-in-Docker (kills risk R1).
FROM ghcr.io/efabless/openlane2:2.3.1

WORKDIR /app
COPY rtl_gauntlet /app/rtl_gauntlet
COPY scripts      /app/scripts
COPY tasks        /app/tasks
COPY deploy/entrypoint.sh /app/deploy/entrypoint.sh

ENV PDK_ROOT=/app/.ciel
# data lands on a Railway volume mounted at /data (or push to a bucket in entrypoint)
CMD ["bash", "/app/deploy/entrypoint.sh"]
