import { screen } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom-v5-compat';
import { render } from 'test/test-utils';

import { PanelProps } from '@grafana/data';
import { getPanelPlugin } from '@grafana/data/test/__mocks__/pluginMocks';
import { selectors } from '@grafana/e2e-selectors';
import { config, setPluginImportUtils } from '@grafana/runtime';
import { Dashboard } from '@grafana/schema';
import { getRouteComponentProps } from 'app/core/navigation/__mocks__/routeProps';
import { DashboardLoaderSrv, setDashboardLoaderSrv } from 'app/features/dashboard/services/DashboardLoaderSrv';
import { getDashboardScenePageStateManager } from 'app/features/dashboard-scene/pages/DashboardScenePageStateManager';

import { DashboardReportPage, Props } from './DashboardReportPage';

jest.mock('@grafana/runtime', () => ({
  ...jest.requireActual('@grafana/runtime'),
  setPluginExtensionGetter: jest.fn(),
  getPluginLinkExtensions: jest.fn(),
  getBackendSrv: () => {
    return {
      get: jest.fn().mockResolvedValue({ dashboard: defaultDashboard, meta: { url: '' } }),
    };
  },
  getDataSourceSrv: () => {
    return {
      get: jest.fn().mockResolvedValue({}),
      getInstanceSettings: jest.fn().mockResolvedValue({ uid: 'ds1' }),
    };
  },
  getAppEvents: () => ({
    publish: jest.fn(),
  }),
}));

const loadDashboardMock = jest.fn();

function setup(path = '/my-dash-uid', dashboard = defaultDashboard) {
  const props: Props = {
    ...getRouteComponentProps(),
  };
  loadDashboardMock.mockResolvedValue({ dashboard: dashboard, meta: { slug: '123' } });
  return render(
    <Routes>
      <Route path={'/:uid'} element={<DashboardReportPage {...props} />} />
    </Routes>,
    {
      historyOptions: {
        initialEntries: [path],
      },
    }
  );
}

const panelPlugin = getPanelPlugin(
  {
    skipDataQuery: true,
  },
  CustomVizPanel
);

config.panels['custom-viz-panel'] = panelPlugin.meta;

setPluginImportUtils({
  importPanelPlugin: (id: string) => Promise.resolve(panelPlugin),
  getPanelPluginFromCache: (id: string) => undefined,
});

setDashboardLoaderSrv({
  loadDashboard: loadDashboardMock,
  // disabling type checks since this is a test util
  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions
} as unknown as DashboardLoaderSrv);

describe('DashboardReportPage', () => {
  beforeEach(() => {
    getDashboardScenePageStateManager().clearState();
    getDashboardScenePageStateManager().clearDashboardCache();
    getDashboardScenePageStateManager().clearSceneCache();
    loadDashboardMock.mockClear();
    // loadDashboardMock.mockResolvedValue({ dashboard: dashboard, meta: { slug: '123' } });
    // This is a hack way of mocking the resizeObserver used to calculate the header height
    Object.defineProperty(HTMLDivElement.prototype, 'offsetHeight', { configurable: true, value: 90 });
  });

  it('Can render dashboard with repeating panels', async () => {
    setup();

    await waitForDashboardToRender();

    expect(await screen.findByTitle('First panel')).toBeVisible();
    expect(await screen.findByText('First content')).toBeVisible();

    const variables = defaultDashboard.templating!.list![0].options || [];
    for (let i = 0; i < variables.length; i++) {
      expect(await screen.findByTitle(`Panel ${variables[i].value}`)).toBeVisible();
    }
    expect(await screen.findAllByText('Repeating content')).toHaveLength(variables.length);
  });

  it('Should use URL values to render repeating panels', async () => {
    setup('/my-dash-uid?var-myVar=A');

    await waitForDashboardToRender();

    expect(await screen.findByTitle('First panel')).toBeVisible();
    expect(await screen.findByText('First content')).toBeVisible();

    expect(await screen.findByTitle('Panel A')).toBeVisible();
    expect(await screen.findByText('Repeating content')).toBeVisible();

    expect(screen.queryByTitle('Panel B')).not.toBeInTheDocument();
    expect(screen.queryByTitle('Panel C')).not.toBeInTheDocument();
  });

  it('Can render dashboard with repeating rows', async () => {
    setup('/my-dash-uid?var-myVar=A');

    await waitForDashboardToRender();

    expect(await screen.findByTitle('First panel')).toBeVisible();
    expect(await screen.findByText('First content')).toBeVisible();

    const variables = defaultDashboard.templating!.list![1].options || [];
    for (let i = 0; i < variables.length; i++) {
      expect(await screen.findByText(`Row title ${variables[i].value}`)).toBeVisible();
    }
    expect(await screen.findAllByText('Content inside repeating row')).toHaveLength(variables.length);
  });

  it('Should use URL values to render repeating rows', async () => {
    setup('/my-dash-uid?var-myVar=A&var-myOtherVar=X');

    await waitForDashboardToRender();

    expect(await screen.findByTitle('First panel')).toBeVisible();
    expect(await screen.findByText('First content')).toBeVisible();

    expect(await screen.findByText('Row title X')).toBeVisible();
    expect(await screen.findByText('Content inside repeating row')).toBeVisible();

    expect(screen.queryByText('Row title Y')).not.toBeInTheDocument();
    expect(screen.queryByText('Row title Z')).not.toBeInTheDocument();
  });

  it('Should use URL values to render time range', async () => {
    setup('/my-dash-uid?var-myVar=A&var-myOtherVar=X&from=1727906400000&to=1727992799999&timezone=Europe/Paris');

    await waitForDashboardToRender();

    // We expect 2 pages + the hidden header used to calculate the header height
    expect(await screen.findAllByText('2024-10-03 00:00:00 +02:00', { exact: false })).toHaveLength(3);
    expect(await screen.findAllByText('2024-10-03 23:59:59 +02:00', { exact: false })).toHaveLength(3);
  });

  it('Should display template variables when the flag pdf.showTemplateVariables is true', async () => {
    setup('/my-dash-uid?var-myVar=A&var-myOtherVar=X&pdf.showTemplateVariables');

    await waitForDashboardToRender();

    // We expect 2 pages + the hidden header used to calculate the header height
    const totalHeadersRendered = 3;
    expect(await screen.findAllByTestId(selectors.pages.Dashboard.SubMenu.submenuItem)).toHaveLength(
      totalHeadersRendered * 2
    );
    expect(await screen.findAllByTestId(selectors.pages.Dashboard.SubMenu.submenuItemLabels('myVar'))).toHaveLength(
      totalHeadersRendered
    );
    expect(
      await screen.findAllByTestId(selectors.pages.Dashboard.SubMenu.submenuItemLabels('myOtherVar'))
    ).toHaveLength(totalHeadersRendered);
  });

  it('Should not display template variables when the flag pdf.showTemplateVariables is false', async () => {
    setup('/my-dash-uid?var-myVar=A&var-myOtherVar=X&pdf.showTemplateVariables=false');

    await waitForDashboardToRender();
    expect(screen.queryByTestId(selectors.pages.Dashboard.SubMenu.submenuItem)).not.toBeInTheDocument();
  });

  it('Should render three pages when using portrait and simple layout', async () => {
    setup('/my-dash-uid?pdf.landscape=false&pdf.layout=simple');

    await waitForDashboardToRender();

    const totalPagesExpected = 3;
    await assertPageNumbersInFooter(totalPagesExpected);
    expect(await screen.findAllByAltText('Report logo')).toHaveLength(totalPagesExpected);
  });

  it('Should render three pages when using portrait and grid layout', async () => {
    setup('/my-dash-uid?pdf.landscape=false&pdf.layout=grid');

    await waitForDashboardToRender();

    const totalPagesExpected = 3;
    await assertPageNumbersInFooter(totalPagesExpected);
    expect(await screen.findAllByAltText('Report logo')).toHaveLength(totalPagesExpected);
  });

  it('Should render one page per panel when using landscape and simple layout', async () => {
    setup('/my-dash-uid?pdf.landscape&pdf.layout=simple');

    await waitForDashboardToRender();

    // 1 panel at the beginning, 3 panels for myVar, 3 panels for myOtherVar
    const totalPagesExpected = 7;
    await assertPageNumbersInFooter(totalPagesExpected);
    expect(await screen.findAllByAltText('Report logo')).toHaveLength(totalPagesExpected);
  });

  it('Should render one row and panel for each variable value using repeating rows', async () => {
    setup(
      '/my-dash-uid?var-myVar=A&var-myVar=B&var-myVar=C&var-myOtherVar=X&var-myOtherVar=Y&var-myOtherVar=Z&pdf.landscape&pdf.layout=simple'
    );

    await waitForDashboardToRender();

    // 1 panel at the beginning, 3 panels for myVar, 3 panels for myOtherVar
    const totalPagesExpected = 7;
    await assertPageNumbersInFooter(totalPagesExpected);
    expect(await screen.findAllByAltText('Report logo')).toHaveLength(totalPagesExpected);
  });

  it('Should render one row and panel for each variable value using repeating inside collapsed rows', async () => {
    setup(
      '/my-dash-uid?var-myVar=A&var-myVar=B&var-myVar=C&var-myOtherVar=X&var-myOtherVar=Y&var-myOtherVar=Z&pdf.landscape&pdf.layout=simple',
      dashboardWithCollapsedRows
    );

    await waitForDashboardToRender();

    // 1 panel at the beginning, 3 panels for myVar, 3 panels for myOtherVar
    const totalPagesExpected = 7;
    await assertPageNumbersInFooter(totalPagesExpected);
    expect(await screen.findAllByAltText('Report logo')).toHaveLength(totalPagesExpected);
  });
});

const defaultDashboard: Dashboard = {
  title: 'My cool dashboard',
  uid: 'my-dash-uid',
  schemaVersion: 30,
  version: 1,
  panels: [
    {
      id: 1,
      type: 'custom-viz-panel',
      title: 'First panel',
      options: {
        content: 'First content',
      },
      gridPos: {
        x: 0,
        y: 0,
        w: 10,
        h: 10,
      },
      targets: [],
    },
    {
      id: 2,
      type: 'custom-viz-panel',
      title: 'Panel ${myVar}',
      options: {
        content: 'Repeating content',
      },
      repeat: 'myVar',
      repeatDirection: 'h',
      gridPos: {
        x: 0,
        y: 10,
        w: 10,
        h: 10,
      },
      targets: [],
    },
    {
      collapsed: false,
      gridPos: {
        h: 1,
        w: 24,
        x: 0,
        y: 20,
      },
      id: 3,
      panels: [],
      repeat: 'myOtherVar',
      title: 'Row title ${myOtherVar}',
      type: 'row',
    },
    {
      id: 4,
      type: 'custom-viz-panel',
      title: 'Panel inside row ${myOtherVar}',
      options: {
        content: 'Content inside repeating row',
      },
      gridPos: {
        x: 0,
        y: 31,
        w: 10,
        h: 10,
      },
      targets: [],
    },
  ],
  templating: {
    list: [
      {
        current: {
          text: ['$__all'],
          value: ['$__all'],
        },
        includeAll: true,
        multi: true,
        name: 'myVar',
        options: [
          { selected: false, text: 'A', value: 'A' },
          { selected: false, text: 'B', value: 'B' },
          { selected: false, text: 'C', value: 'C' },
        ],
        query: 'A,B,C',
        type: 'custom',
      },
      {
        current: {
          text: ['$__all'],
          value: ['$__all'],
        },
        includeAll: true,
        multi: true,
        name: 'myOtherVar',
        options: [
          { selected: false, text: 'X', value: 'X' },
          { selected: false, text: 'Y', value: 'Y' },
          { selected: false, text: 'Z', value: 'Z' },
        ],
        query: 'X,Y,Z',
        type: 'custom',
      },
    ],
  },
};

const dashboardWithCollapsedRows: Dashboard = {
  title: 'My cool dashboard',
  uid: 'my-dash-uid',
  schemaVersion: 30,
  version: 1,
  panels: [
    {
      id: 1,
      type: 'custom-viz-panel',
      title: 'First panel',
      options: {
        content: 'First content',
      },
      gridPos: {
        x: 0,
        y: 0,
        w: 10,
        h: 10,
      },
      targets: [],
    },
    {
      id: 2,
      type: 'custom-viz-panel',
      title: 'Panel ${myVar}',
      options: {
        content: 'Repeating content',
      },
      repeat: 'myVar',
      repeatDirection: 'h',
      gridPos: {
        x: 0,
        y: 10,
        w: 10,
        h: 10,
      },
      targets: [],
    },
    {
      collapsed: true,
      gridPos: {
        h: 1,
        w: 24,
        x: 0,
        y: 20,
      },
      id: 3,
      panels: [
        {
          id: 4,
          type: 'custom-viz-panel',
          title: 'Panel inside row ${myOtherVar}',
          options: {
            content: 'Content inside repeating row',
          },
          gridPos: {
            x: 0,
            y: 31,
            w: 10,
            h: 10,
          },
          targets: [],
        },
      ],
      repeat: 'myOtherVar',
      title: 'Row title ${myOtherVar}',
      type: 'row',
    },
  ],
  templating: {
    list: [
      {
        current: {
          text: ['$__all'],
          value: ['$__all'],
        },
        includeAll: true,
        multi: true,
        name: 'myVar',
        options: [
          { selected: false, text: 'A', value: 'A' },
          { selected: false, text: 'B', value: 'B' },
          { selected: false, text: 'C', value: 'C' },
        ],
        query: 'A,B,C',
        type: 'custom',
      },
      {
        current: {
          text: ['$__all'],
          value: ['$__all'],
        },
        includeAll: true,
        multi: true,
        name: 'myOtherVar',
        options: [
          { selected: false, text: 'X', value: 'X' },
          { selected: false, text: 'Y', value: 'Y' },
          { selected: false, text: 'Z', value: 'Z' },
        ],
        query: 'X,Y,Z',
        type: 'custom',
      },
    ],
  },
};
interface VizOptions {
  content: string;
}
interface VizProps extends PanelProps<VizOptions> {}

function CustomVizPanel(props: VizProps) {
  return <div>{props.options.content}</div>;
}

async function waitForDashboardToRender() {
  expect(await screen.findByTitle('Panel A')).toBeInTheDocument();
}

async function assertPageNumbersInFooter(expectedPages: number) {
  for (let i = 1; i <= expectedPages; i++) {
    expect(await screen.findByText(`Page ${i}/${expectedPages}`)).toBeVisible();
  }
}
