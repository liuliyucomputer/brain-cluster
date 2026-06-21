import { featureEnabled } from '@grafana/runtime';
import { SceneComponentProps, SceneObjectBase } from '@grafana/scenes';
import { highlightTrial } from 'app/features/admin/utils';
import { SceneShareTabState, ShareView } from 'app/features/dashboard-scene/sharing/types';
import { getDashboardSceneFor } from 'app/features/dashboard-scene/utils/utils';

import { ReportBaseV2 } from '../../types';
import ReportForm from '../ReportFormV2/ReportForm';

import { HighlightTrialReport } from './HighlightTrialReport';
import { UpgradeReport } from './UpgradeReport';

export class ShareReport extends SceneObjectBase<SceneShareTabState> implements ShareView {
  static Component = ShareReportRenderer;

  public getTabLabel() {
    return 'Schedule report';
  }
}

function ShareReportRenderer({ model }: SceneComponentProps<ShareReport>) {
  const isReportsCreationDisabled = !featureEnabled('reports.creation');
  const dashboard = getDashboardSceneFor(model);

  if (isReportsCreationDisabled) {
    return <UpgradeReport />;
  }

  const report: Partial<ReportBaseV2> = {
    name: dashboard.state.title,
    dashboards: [
      {
        dashboard: {
          uid: dashboard.state.uid!,
          name: dashboard.state.title,
        },
        reportVariables: {},
        timeRange: {
          from: dashboard.state.$timeRange?.state.from ?? '',
          to: dashboard.state.$timeRange?.state.to ?? '',
        },
      },
    ],
  };

  return (
    <>
      {highlightTrial() && <HighlightTrialReport />}
      <ReportForm report={report} />
    </>
  );
}
