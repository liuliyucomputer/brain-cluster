import { css } from '@emotion/css';
import { useState } from 'react';
import { connect, ConnectedProps } from 'react-redux';

import { GrafanaTheme2 } from '@grafana/data';
import { locationService } from '@grafana/runtime';
import { Button, ConfirmModal, IconButton, LinkButton, useStyles2 } from '@grafana/ui';
import { contextSrv } from 'app/core/services/context_srv';

import { AccessControlAction, EnterpriseStoreState, ReportState, StepKey } from '../../types';
import { REPORT_BASE_URL } from '../constants';
import { deleteReport, loadReport, updateReport } from '../state/actions';
import { getButtonText } from '../utils/pageActions';
import { getReportStateInfo, getToggledReportState } from '../utils/reportState';
import { getSectionUrl } from '../utils/url';

const mapStateToProps = (state: EnterpriseStoreState) => {
  const { report } = state.reports;
  return {
    report,
  };
};

const mapActionsToProps = {
  loadReport,
  deleteReport,
  updateReport,
};

type OwnProps = {
  reportId?: string;
  disabled?: boolean;
};

const connector = connect(mapStateToProps, mapActionsToProps);
export type Props = ConnectedProps<typeof connector> & OwnProps;

export const EditActions = ({ report, loadReport, deleteReport, updateReport, disabled }: Props) => {
  const styles = useStyles2(getStyles);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const canDeleteReport = contextSrv.hasPermission(AccessControlAction.ReportingDelete);
  const canEditReport = contextSrv.hasPermission(AccessControlAction.ReportingWrite);
  const { showPlay, disableEdit, reportState } = getReportStateInfo(report);
  const onToggleReportState = async () => {
    const newState = getToggledReportState(reportState);

    // api call to update report data
    await updateReport({
      ...report,
      state: newState,
    });

    // Update report data on state
    if (report.id) {
      loadReport(report.id);
    }
  };

  const onDeleteReport = () => {
    deleteReport(report.id);
    setIsModalOpen(false);
    locationService.push(REPORT_BASE_URL);
  };

  return (
    <div className={styles.editActions}>
      <LinkButton href={getSectionUrl(StepKey.SelectDashboard, report.id)} type={'button'} disabled={!canEditReport}>
        Edit report
      </LinkButton>

      <Button
        type="button"
        variant="secondary"
        disabled={disableEdit || !canEditReport || disabled}
        onClick={onToggleReportState}
      >
        {showPlay ? (reportState === ReportState.Draft ? getButtonText(report.schedule) : 'Resume') : 'Pause'}
      </Button>
      <IconButton
        variant="destructive"
        aria-label="Delete report"
        tooltip="Delete"
        name="trash-alt"
        disabled={!canDeleteReport}
        onClick={() => setIsModalOpen(true)}
      />
      <ConfirmModal
        isOpen={isModalOpen}
        title="Delete report"
        body="Are you sure you want to delete this report?"
        confirmText="Delete"
        onConfirm={onDeleteReport}
        onDismiss={() => setIsModalOpen(false)}
      />
    </div>
  );
};

const getStyles = (theme: GrafanaTheme2) => {
  return {
    editActions: css({
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'flex-end',
      width: '100%',
      marginBottom: theme.spacing(3),

      'button, a': {
        marginLeft: theme.spacing(2),
      },
    }),
  };
};

export default connector(EditActions);
