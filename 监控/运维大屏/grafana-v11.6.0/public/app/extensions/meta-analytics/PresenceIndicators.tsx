import { isEqual } from 'lodash';
import { FC, useState, useEffect } from 'react';
import * as React from 'react';
import { connect, ConnectedProps } from 'react-redux';

import { UsersIndicator } from '@grafana/ui/src/components/UsersIndicator/UsersIndicator';
import { contextSrv } from 'app/core/services/context_srv';
import { addCustomLeftAction } from 'app/features/dashboard/components/DashNav/DashNav';
import { DashboardModel } from 'app/features/dashboard/state/DashboardModel';

import { AccessControlAction, AnalyticsTab } from '../types';

import { getRecentUsers, UserViewDTO } from './api';
import { openDrawer } from './state/actions';

export interface Props {
  dashboard?: DashboardModel;
}

const mapDispatchToProps = {
  openDrawer,
};

const connector = connect(null, mapDispatchToProps);
export type PresenceIndicatorsProps = ConnectedProps<typeof connector> & Props;

const iconLimit = 4;
const refreshInterval = 60000; // In milliseconds

function fetchRecentUsers(dashboardUid: string, setRecentUsers: React.Dispatch<React.SetStateAction<UserViewDTO[]>>) {
  const user = contextSrv.user;
  getRecentUsers(dashboardUid, iconLimit + 10).then((data) => {
    const items = data.filter((item: UserViewDTO) => item.user.id !== user.id);
    setRecentUsers((recentUsers: UserViewDTO[]) => (isEqual(items, recentUsers) ? recentUsers : items));
  });
}

export const PresenceIndicators: FC<PresenceIndicatorsProps> = ({ dashboard, openDrawer }) => {
  const dashboardUid = dashboard?.uid;
  const [recentUsers, setRecentUsers] = useState<UserViewDTO[]>([]);

  useEffect(() => {
    if (!dashboardUid || !dashboard?.meta.url) {
      return undefined;
    }

    fetchRecentUsers(dashboardUid, setRecentUsers);
    const interval = setInterval(() => fetchRecentUsers(dashboardUid, setRecentUsers), refreshInterval);
    return () => {
      clearInterval(interval);
    };
  }, [dashboardUid, dashboard]);

  return <UsersIndicator users={recentUsers} limit={iconLimit} onClick={() => openDrawer(AnalyticsTab.Users)} />;
};

export const initPresenceIndicators = () => {
  if (contextSrv.hasPermission(AccessControlAction.DashboardsInsightsRead)) {
    addCustomLeftAction({
      show: () => true,
      component: connector(PresenceIndicators),
      index: 'end',
    });
  }
};
