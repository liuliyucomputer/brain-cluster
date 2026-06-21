import { DataSourceJsonData, DataSourceSettings } from '@grafana/data';
import { ResourcePermission } from 'app/core/components/AccessControl/types';
import { config } from 'app/core/config';
import { t } from 'app/core/internationalization';

import { TeamRule } from '../types';

export const LBACHTTPHeaderName = 'X-Prom-Label-Policy';

export function hasLBACSupport(ds: DataSourceSettings<DataSourceJsonData, {}>): boolean {
  let DataSourcesWithLBACSupport = ['loki'];
  if (config.featureToggles.teamHttpHeadersMimir) {
    DataSourcesWithLBACSupport = ['loki', 'prometheus'];
  }
  return !!ds.basicAuth && DataSourcesWithLBACSupport.includes(ds.type);
}

export function trimLBACRule(rule: string) {
  const pattern = /\{([^{}]*)\}/;
  const res = pattern.exec(rule);
  if (res && res.length > 1) {
    return res[1].trim();
  }
  return '';
}

export function formatLBACRule(labelSelector: string) {
  const pattern = /\{{0,1}([^\{\}]*)\}{0,1}/;
  const res = pattern.exec(labelSelector);
  if (res && res.length > 1) {
    return `{ ${res[1].trim()} }`;
  }
  return '';
}

export function extractLBACRule(rule: string) {
  const pattern = /\w+\:\{{0,1}([^\{\}]*)\}{0,1}/;
  const res = pattern.exec(rule);
  if (res && res.length > 1) {
    return res[1].trim();
  }
  return '';
}

export const validateLBACRule = (str: string): boolean => {
  if (!str) {
    return false;
  }
  const trimmedStr = str.trim().replace(/^{|}$/g, '');
  const pattern = /^\s*(?:\s*\w+\s*(?:=|!=|=~|!~)\s*\"[^\"]+\"\s*,*)+\s*$/;
  return pattern.test(trimmedStr);
};

export const getLBACTeamsConfigured = (rules: TeamRule[]): string[] => {
  const teams: string[] = [];
  if (rules.length) {
    rules.forEach((rule) => {
      if (rule.teamUid) {
        teams.push(rule.teamUid);
      }
    });
  }
  return teams;
};

export const addTeamLBACWarnings = (teams: string[], items: ResourcePermission[]) => {
  const warningTeam = t(
    'access-control.permissions.lbac-warning-team',
    'Warning: This team has full data access if no LBAC rules are set.'
  );
  return items.map((item) => {
    if (item.builtInRole && item.permission !== 'Admin') {
      const warningBasicRole = t(
        'access-control.permissions.lbac-warning-basic-role',
        `Warning: ${item.builtInRole} may have full data access if permission is not removed.`
      );
      item.warning = warningBasicRole;
    } else if (item.teamUid && !teams.includes(item.teamUid)) {
      item.warning = warningTeam;
    }
    return { ...item };
  });
};

export const addTeamLBACWarningsToLBACRule = (teams: string[], items: TeamRule[]) => {
  const warningTeam = t(
    'access-control.permissions.lbac-warning-rule',
    'Warning: This team might not have permission to the query the datasource.'
  );
  return items.map((item) => {
    if (item.teamUid && !teams.includes(item.teamUid)) {
      item.warning = warningTeam;
    }
    return { ...item };
  });
};
