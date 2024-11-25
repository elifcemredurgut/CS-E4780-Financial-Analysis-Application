FROM flink:1.17.1

# Versions
ENV \
  # Python
  PYTHON_VER=3.10.13 \
  # PyFlink
  APACHE_FLINK_VER=1.17.1
  
SHELL ["/bin/bash", "-ceuxo", "pipefail"]

RUN apt-get update -y && \
  apt-get install -y --no-install-recommends \
    build-essential libssl-dev zlib1g-dev libbz2-dev libffi-dev lzma liblzma-dev \
    openjdk-11-jdk \
  && \
  wget -q "https://www.python.org/ftp/python/${PYTHON_VER}/Python-${PYTHON_VER}.tar.xz" && \
  tar -xf "Python-${PYTHON_VER}.tar.xz" && \
  cd "Python-${PYTHON_VER}" && \
  ./configure --enable-optimizations --without-tests --enable-shared && \
  make -j$(nproc) && \
  make install && \
  ldconfig /usr/local/lib && \
  cd .. && \
  rm -rf "Python-${PYTHON_VER}" "Python-${PYTHON_VER}.tar.xz" && \
  ln -s /usr/local/bin/python3 /usr/local/bin/python && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# Installing OpenJDK again & setting - this is required due to a bug with M1 Macs
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-arm64

RUN pip3 install --no-cache-dir apache-flink==${APACHE_FLINK_VER} && \
  pip3 cache purge

RUN pip3 install psycopg2-binary

RUN wget -P /opt/flink/lib/ https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.3.0-1.20/flink-sql-connector-kafka-3.3.0-1.20.jar;
RUN wget -P /opt/flink/lib/ https://repo.maven.apache.org/maven2/org/apache/flink/flink-connector-jdbc/3.1.1-1.17/flink-connector-jdbc-3.1.1-1.17.jar;
RUN wget -P /opt/flink/lib/ https://jdbc.postgresql.org/download/postgresql-42.7.4.jar

# Copy your PyFlink job script into the container
COPY flink_job_ema.py /opt/flink_job_ema.py
COPY flink_job_price.py /opt/flink_job_price.py
COPY flink_job_same_window.py /opt/flink_job_same_window.py
COPY flink_job_topic_read.py /opt/flink_job_topic_read.py
# Set the default command to start the Flink JobManager or TaskManager
CMD ["jobmanager"]

# Install python3.7 and pyflink
# Pyflink does not yet function with python3.9, and this image is build on
# debian bullseye which ships with that version, so build python3.7 here.

#RUN apt-get update && apt-get install -y python3 python3-pip
#RUN pip3 install kafka-python protobuf
#RUN ln -s /usr/bin/python3 /usr/bin/python
#RUN ln -s /usr/bin/python3 python
#RUN python -m pip install apache-flink
#RUN pip install apache-flink==1.20.0; \
#RUN pip install kafka-python;
