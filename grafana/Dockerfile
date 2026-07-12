FROM grafana/grafana:11.6.16-ubuntu

ENV GF_ANALYTICS_REPORTING_ENABLED=false \
    GF_ANALYTICS_CHECK_FOR_UPDATES=false \
    GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES=false \
    GF_USERS_ALLOW_SIGN_UP=false \
    GF_AUTH_DISABLE_LOGIN_FORM=true \
    GF_AUTH_BASIC_ENABLED=false \
    GF_AUTH_ANONYMOUS_ENABLED=false \
    GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH=/etc/grafana/dashboards/bi-home.json

COPY provisioning /etc/grafana/provisioning
COPY dashboards /etc/grafana/dashboards
