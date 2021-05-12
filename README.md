If you are doing remote-only exporter foo, use the [soundcloud ipmi\_exporter](https://github.com/soundcloud/ipmi_exporter). This is for using with a "device" mount to `/dev/ipmi0`.

The `node_` names were chosen to backfill stats that would otherwise come via the prometheus node\_exporter. Currently those are `node_ipmi_speed_rpm` and `node_hwmon_temp_celsius`.

Basic docker run:

    docker run -p 9999:9999 -it --device=/dev/ipmi0 ipmi

TODO: docker-compose
