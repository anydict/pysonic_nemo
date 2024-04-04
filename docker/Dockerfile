FROM python:3.12.2-slim

ENV LD_LIBRARY_PATH=/usr/local/lib
COPY --from=jrottenberg/ffmpeg /usr/local /usr/local/

EXPOSE 7005
EXPOSE 1234

WORKDIR /opt/pysonic_nemo

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

COPY ./ .

CMD ["python", "run_pysonic_nemo.py"]
