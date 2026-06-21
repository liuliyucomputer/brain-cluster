export interface TeamLBACState {
  teamLBACConfig: TeamLBACConfig;
}

export interface TeamLBACConfig {
  rules?: TeamRule[];
}

export interface TeamRule {
  teamUid: string;
  rules: string[];
  warning?: string;
}
