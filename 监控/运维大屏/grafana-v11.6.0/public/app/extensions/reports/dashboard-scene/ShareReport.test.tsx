import { screen } from '@testing-library/react';
import { render } from 'test/test-utils';

import { getPanelPlugin } from '@grafana/data/test/__mocks__/pluginMocks';
import { featureEnabled, setPluginImportUtils } from '@grafana/runtime';
import { SceneComponentProps, VizPanel, SceneTimeRange } from '@grafana/scenes';
import { highlightTrial } from 'app/features/admin/utils';
import { DashboardScene } from 'app/features/dashboard-scene/scene/DashboardScene';
import { DefaultGridLayoutManager } from 'app/features/dashboard-scene/scene/layout-default/DefaultGridLayoutManager';
import { activateFullSceneTree } from 'app/features/dashboard-scene/utils/test-utils';

import { selectors } from '../e2e-selectors/selectors';

import { ShareReport } from './ShareReport';

// Mocking external dependencies
jest.mock('@grafana/runtime', () => ({
  ...jest.requireActual('@grafana/runtime'),
  featureEnabled: jest.fn(),
  reportInteraction: jest.fn(),
  getBackendSrv: () => ({
    get: jest.fn().mockResolvedValue({
      meta: {
        isFolder: false,
        canSave: true,
        canEdit: true,
      },
      dashboard: {
        id: 1,
        title: 'hello',
        uid: 'dash-1',
      },
    }),
  }),
}));

setPluginImportUtils({
  importPanelPlugin: (id: string) => Promise.resolve(getPanelPlugin({})),
  getPanelPluginFromCache: (id: string) => undefined,
});

jest.mock('../../../features/admin/utils', () => ({
  ...jest.requireActual('app/features/admin/utils'),
  highlightTrial: jest.fn(),
}));

const renderComponent = (props: Partial<SceneComponentProps<ShareReport>> = {}) => {
  const shareReport = new ShareReport({});

  const panel = new VizPanel({
    title: 'Panel A',
    pluginId: 'table',
    key: 'panel-12',
  });

  const scene = new DashboardScene({
    title: 'hello',
    uid: 'dash-1',
    meta: {
      canEdit: true,
    },
    $timeRange: new SceneTimeRange({}),
    body: DefaultGridLayoutManager.fromVizPanels([panel]),
    overlay: shareReport,
  });

  shareReport.activate();
  activateFullSceneTree(scene);

  return render(<shareReport.Component model={shareReport} />);
};

describe('ShareReport', () => {
  beforeEach(() => {
    (featureEnabled as jest.Mock).mockReturnValue(true);
    (highlightTrial as jest.Mock).mockReturnValue(false);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should render the new drawer content when reports creation is enabled without highlight trial', async () => {
    renderComponent();
    expect(await screen.findByTestId(selectors.components.ReportFormDrawer.container)).toBeInTheDocument();
    expect(screen.queryByText('Learn more')).not.toBeInTheDocument();
    expect(screen.queryByText('Get started with reporting')).not.toBeInTheDocument();
  });

  it('should render the new drawer content when reports creation is enabled with highlight trial', async () => {
    (highlightTrial as jest.Mock).mockReturnValue(true);

    renderComponent();
    expect(await screen.findByTestId(selectors.components.ReportFormDrawer.container)).toBeInTheDocument();
    expect(screen.queryByText('Learn more')).toBeInTheDocument();
    expect(screen.queryByText('Get started with reporting')).toBeInTheDocument();
  });

  it('should not render the report form when report is disabled and should render feature description', async () => {
    (featureEnabled as jest.Mock).mockReturnValue(false);

    renderComponent();
    expect(screen.queryByTestId(selectors.components.ReportFormDrawer.container)).not.toBeInTheDocument();
    expect(
      await screen.findByText(
        'Reporting allows you to automatically generate PDFs from any of your dashboards and have Grafana email them to interested parties on a schedule.'
      )
    ).toBeInTheDocument();
  });
});
