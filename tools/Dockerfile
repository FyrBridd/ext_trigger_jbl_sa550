FROM kicad/kicad:10.0
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3-pip python3-venv gcc libc6-dev make gcc-avr avr-libc binutils-avr \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv --system-site-packages /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir kicad-sch-api==0.5.5 pytest
ENV PATH=/opt/venv/bin:$PATH
