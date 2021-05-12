FROM ubuntu:20.04

RUN apt update && apt install -y python3-pip ipmitool
RUN pip3 install docker prometheus_client sarge
COPY ipmi_exporter.py /opt/app/ipmi_exporter.py

EXPOSE 9999

CMD python3 /opt/app/ipmi_exporter.py
