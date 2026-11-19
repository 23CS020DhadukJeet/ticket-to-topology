FROM python:3.12-slim AS build
WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir build && python -m build --wheel

FROM python:3.12-slim
RUN useradd --create-home --uid 10001 t2t
RUN mkdir /data && chown t2t /data
COPY --from=build /src/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl
USER t2t
WORKDIR /home/t2t
ENV T2T_DB_PATH=/data/t2t.db
VOLUME ["/data"]
ENTRYPOINT ["t2t"]
CMD ["--help"]
