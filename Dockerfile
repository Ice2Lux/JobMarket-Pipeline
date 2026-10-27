FROM prodazfrz6sh.azurecr.io/pod-base:prefect-spark-3.5-py311

RUN mkdir -p /work/workflow

COPY pip.conf /etc/pip.conf
COPY requirements.txt constraints.txt setup.py /work/

RUN pip install --no-cache-dir -e . -r requirements.txt -c constraints.txt

COPY workflow /work/workflow/

ARG _GITHUB_REPOSITORY
ARG _GITHUB_SHA

ENV GITHUB_REPOSITORY=${_GITHUB_REPOSITORY}
ENV GITHUB_SHA=${_GITHUB_SHA}