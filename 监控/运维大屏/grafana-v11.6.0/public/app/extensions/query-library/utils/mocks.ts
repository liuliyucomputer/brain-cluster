import { PromQuery } from "@grafana/prometheus";

import { QueryTemplateRow } from "../types";

export const mockQuery: PromQuery = {
  refId: 'A',
  datasource: {
    uid: 'Prometheus0',
    type: 'prometheus',
  },
  expr: 'go_gc_pauses_seconds_count{instance=\"host.docker.internal:3000\"}',
}

export const mockQueryTemplateRow: QueryTemplateRow = {
  index: '0',
  uid: '0',
  datasourceName: 'prometheus',
  datasourceRef: { type: 'prometheus', uid: 'Prometheus0' },
  datasourceType: 'prometheus',
  createdAtTimestamp: 0,
  query: mockQuery,
  queryText: 'http_requests_total{job="test"}',
  description: 'template0',
  user: {
    uid: 'viewer:JohnDoe',
    displayName: 'John Doe',
    avatarUrl: 'johnDoeAvatarUrl',
  },
}
