#!/usr/bin/env python3

import sarge
import json
import prometheus_client
import logging
import os
import time
import re
import statistics

log = logging.getLogger(os.path.basename(__file__))
log.setLevel(logging.DEBUG)

# time to sleep between scrapes
UPDATE_PERIOD = int(os.environ.get('UPDATE_PERIOD', 30))


FAN_SPEED = prometheus_client.Gauge('node_ipmi_speed_rpm',
                              "the air blowy thing spins. heres its speed.",
                              ['sensor'])
FAN_HEALTH = prometheus_client.Gauge('fan_health_count',
                              "simple yes/no for fan health. assumed to always be spinning, so zero is bad.",
                              ['state'])
POWER = prometheus_client.Gauge('power_state',
                              "volts, amps, gigawatts, however power is measured.",
                              ['measurement', 'power_supply_num', 'units'])
TEMP = prometheus_client.Gauge('node_hwmon_temp_celsius',
                              "Hardware monitor for temperature.",
                              ['chip', 'sensor'])




#{
#  "raw": {
#    "fan1_rpm": 3480.0,
#    "fan2_rpm": 3480.0,
#    "fan3_rpm": 3480.0,
#    "fan4_rpm": 3480.0,
#    "fan5_rpm": 3480.0,
#    "fan6_rpm": 3480.0,
#    "inlet_temp_degrees_c": 21.0,
#    "current_1_amps": 1.2,
#    "current_2_amps": 0.0,
#    "voltage_1_volts": 124.0,
#    "voltage_2_volts": 126.0,
#    "pwr_consumption_watts": 154.0,
#    "temp_degrees_c": 57.0,
#    "system_level_watts": 154.0
#  },
#  "fan": {
#    "good": 6,
#    "bad": 0,
#    "median": 3480.0,
#    "min": 3480.0,
#    "max": 3480.0
#  }

def collect():
  b = get_bmc()
  print(json.dumps(b, indent=2))
  fan_summary = b['fan']
  FAN_HEALTH.labels('good').set(fan_summary['good'])
  FAN_HEALTH.labels('bad').set(fan_summary['bad'])

  for k, v in b['raw'].items():
    if re.match(r'^fan.*rpm$', k):
      shortlabel = re.sub("_rpm", "", k)
      FAN_SPEED.labels(shortlabel).set(int(v))
    elif m := re.match("(.*?)_?temp_degrees_c", k):
      #print(m.groups(), "/", m.group(1))
      templabel = m.group(1) or 'system'
      TEMP.labels('', templabel).set(v)
      #print(f"got: {templabel}")
    elif m := re.match("(.+?)_?(\d+)?_(volts|watts|amps)", k):
      #print("tri: ", "/".join( (m.group(1), m.group(2) or '', m.group(3)) ), v)
      POWER.labels(m.group(1), m.group(2) or '', m.group(3)).set(v)
    #elif m := re.match("(.+)_watts", k):
    #  POWER.labels(m.group(1), '', m.group(2)).set(v)
    else:
      print(f"nonmatch: {k}")
  #"inlet_temp_degrees_c": 21.0,
    #"inlet_temp_degrees_c": 21.0,
    #"current_1_amps": 1.2,
    #"current_2_amps": 0.0,
    #"voltage_1_volts": 124.0,
    #"voltage_2_volts": 126.0,
    #"pwr_consumption_watts": 154.0,
    #"temp_degrees_c": 57.0,
    #"system_level_watts": 154.0

def get_bmc():
  raw = {}
  sarge_pipe = sarge.capture_both('ipmitool sensor')
  ipmiret = sarge_pipe.stdout.text
  log.debug(f"get run stderr: {sarge_pipe.stderr.text}")

  rc = sarge_pipe.returncode
  errtxt = sarge_pipe.stderr.text
  if rc or errtxt:
    log.error(f"IPMI failed, code: {rc}, text: {errtxt}")
    return

  # | egrep "^(FAN|System Level|Ambient Temp.*degrees C)" | cut -c 1-39 | sort
  for line in ipmiret.splitlines():
    (label,value,units,_) = map(str.strip, line.split("|", 3))
    if re.match(r'^[\d\.]+$', value):
      k_units = units.lower().replace(' ', '_')
      k_label = label.lower().replace(' ', '_')
      if not k_label.endswith(k_units):
        k_label = f'{k_label}_{k_units}'

      raw[k_label] = float(value)
      log.info(f"{k_label} == {value}")

  fan_summary = {'good': 0, 'bad': 0, 'median': 0, 'min': 0, 'max': 0}
  rpms = []
  for k,v in raw.items():
    #print('kk',k,v)
    if re.match(r'^fan.*rpm$', k):

      #print('yey kk',k,v)
      if v > 0.1:
        fan_summary['good'] += 1
        rpms.append(v)
      else:
        fan_summary['bad'] += 1
  if len(rpms):
    fan_summary['median'] = statistics.median_low(rpms)
    fan_summary['min'] = min(rpms)
    fan_summary['max'] = max(rpms)

  return {
    'raw': raw,
    'fan': fan_summary
  }


if __name__ == '__main__':
  prometheus_client.start_http_server(9999)
  while True:
    #log.warning("starting loop.")
    try:
      collect()
      #b = get_bmc()
    except ValueError as ex:
      log.error(f"stats loop failed, {type(ex)}: {ex}")

    # sleep 30 seconds
    time.sleep(UPDATE_PERIOD)
