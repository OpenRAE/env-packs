# Telemetry prompts

- Compare the red activity log with Wazuh manager/indexer/dashboard evidence.
- Check whether Suricata observed the same network events and whether its view
  adds context unavailable at the host layer.
- Determine whether MISP enrichment, TheHive case handling, Cortex analysis,
  or Shuffle automation participated; absence is a finding, not proof that the
  action did not occur.
- Use the ACES dependency graph to explain missing telemetry before attributing
  it to the exercise participant.
- Keep OTEL/Grafana/Tempo platform observability distinct from security-event
  evidence.
