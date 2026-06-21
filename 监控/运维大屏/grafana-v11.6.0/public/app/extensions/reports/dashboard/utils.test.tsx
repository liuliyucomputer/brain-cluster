import { SceneGridItemLike, SceneGridRow, VizPanel } from '@grafana/scenes';

import { DashboardGridItem } from '../../../features/dashboard-scene/scene/layout-default/DashboardGridItem';

import { A4_HEIGHT, A4_WIDTH, FOOTER } from './ReportGridRenderer';
import { buildGridLayout } from './utils';

describe('buildGridLayout', () => {
  it('should build correct layout for large panels and rows', () => {
    const dashboardItems: SceneGridItemLike[] = [
      buildPanel(1, 0, 0, 4, 24, 'Top panel'),
      new SceneGridRow({
        key: 'gridRow-1',
        title: 'First row',
        y: 4,
        children: [buildPanel(2, 0, 5, 6, 12, 'Panel A'), buildPanel(3, 12, 5, 6, 12, 'Panel B')],
      }),
      new SceneGridRow({
        key: 'gridRow-2',
        title: 'Second row',
        y: 11,
        children: [
          buildPanel(4, 0, 12, 17, 24, 'Large panel after row'),
          buildPanel(5, 0, 29, 24, 24, 'Large panel after panel'),
        ],
      }),
    ];
    const scale = 1.5;
    const pages = buildGridLayout(dashboardItems, scale, (A4_HEIGHT - 110 - FOOTER) * scale);

    expect(pages.length).toBe(2);
    expect(pages[0].items.length).toBe(6);
    expect(pages[1].items.length).toBe(1);
  });

  it('panels with the same Y position should remain in the same page', () => {
    const dashboardItems: SceneGridItemLike[] = [
      buildPanel(1, 0, 0, 6, 5, 'Top panel A'),
      buildPanel(2, 12, 0, 10, 10, 'Top panel B'),
      buildPanel(3, 0, 10, 6, 2, 'Panel with Y 5'),
      buildPanel(4, 2, 10, 20, 12, 'Sibling panel with same Y but big height'),
      buildPanel(5, 0, 30, 10, 12, 'Panel in different page'),
      buildPanel(6, 4, 30, 10, 12, 'Panel in different page'),
    ];
    const scale = 1;
    const pages = buildGridLayout(dashboardItems, scale, (A4_WIDTH - 92 - FOOTER) * scale);

    expect(pages.length).toBe(3);
    expect(pages[0].items.length).toBe(2);
    expect(pages[1].items.length).toBe(2);
    expect(pages[2].items.length).toBe(2);
  });

  it('panels with the same Y position should remain in the same page - second case', () => {
    const dashboardItems: SceneGridItemLike[] = [
      buildPanel(1, 0, 0, 10, 12, 'Top panel A'),
      buildPanel(2, 12, 0, 10, 12, 'Top panel B'),
      buildPanel(3, 0, 10, 6, 2, 'Panel with Y 5 and small height'),
      buildPanel(4, 2, 10, 16, 12, 'Sibling panel with same Y but big height'),
      buildPanel(5, 14, 10, 16, 10, 'Sibling panel with same Y but big height'),
      buildPanel(6, 0, 16, 10, 2, 'Panel'),
    ];
    const scale = 1;
    const pages = buildGridLayout(dashboardItems, scale, (A4_WIDTH - 92 - FOOTER) * scale);

    expect(pages.length).toBe(2);
    expect(pages[0].items.length).toBe(2);
    expect(pages[1].items.length).toBe(4);
  });

  it('should build correct layout for horizontal repeated panels within repeating rows', async () => {
    const dashboardItems: SceneGridItemLike[] = [
      new SceneGridRow({
        key: 'gridRow-1',
        title: 'First row',
        y: 0,
        children: [buildRepeatedPanel(1, 0, 1, 24, 24, 'Repeated panel', 6)],
      }),
      new SceneGridRow({
        key: 'gridRow-2',
        title: 'Second row',
        y: 9,
        children: [buildRepeatedPanel(2, 0, 10, 24, 24, 'Repeated panel', 6)],
      }),
    ];

    const scale = 1;
    const pages = buildGridLayout(dashboardItems, scale, (A4_WIDTH - 110 - FOOTER) * scale);

    expect(pages.length).toBe(3);
    expect(pages[0].items.length).toBe(5);
    expect(pages[1].items.length).toBe(5);
    expect(pages[2].items.length).toBe(4);
  });

  it('should build correct layout for horizontal repeated panels followed by other panels', async () => {
    const dashboardItems: SceneGridItemLike[] = [
      buildPanel(1, 0, 0, 8, 12, 'First panel'),
      buildRepeatedPanel(2, 0, 8, 24, 24, 'Repeated panel', 6),
      buildPanel(3, 0, 32, 8, 12, 'Last panel'),
    ];

    const scale = 1;
    const pages = buildGridLayout(dashboardItems, scale, (A4_WIDTH - 110 - FOOTER) * scale);

    expect(pages.length).toBe(3);
    expect(pages[0].items.length).toBe(3);
    expect(pages[1].items.length).toBe(4);
    expect(pages[2].items.length).toBe(1);
  });

  it('should build correct layout for vertical repeated panels within repeating rows', async () => {
    const dashboardItems: SceneGridItemLike[] = [
      new SceneGridRow({
        key: 'gridRow-1',
        title: 'First row',
        y: 0,
        children: [
          buildRepeatedPanel(1, 0, 1, 9, 5, 'Repeated panel 1', 3),
          buildRepeatedPanel(2, 5, 1, 12, 5, 'Repeated panel 2', 3),
          buildRepeatedPanel(3, 10, 1, 9, 14, 'Repeated panel 3', 3),
        ],
      }),
      new SceneGridRow({
        key: 'gridRow-2',
        title: 'Second row',
        y: 5,
        children: [
          buildRepeatedPanel(4, 0, 6, 9, 5, 'Repeated panel 1', 3),
          buildRepeatedPanel(5, 5, 6, 12, 5, 'Repeated panel 2', 3),
          buildRepeatedPanel(6, 10, 6, 9, 14, 'Repeated panel 3', 3),
        ],
      }),
      new SceneGridRow({
        key: 'gridRow-3',
        title: 'Final row',
        y: 10,
        children: [buildPanel(7, 0, 11, 6, 12, 'Last panel')],
      }),
    ];

    const scale = 1;
    const pages = buildGridLayout(dashboardItems, scale, (A4_WIDTH - 110 - FOOTER) * scale);

    expect(pages.length).toBe(2);
    expect(pages[0].items.length).toBe(19);
    expect(pages[1].items.length).toBe(3);
  });
});

function buildPanel(index: number, x: number, y: number, h: number, w: number, title: string): DashboardGridItem {
  return new DashboardGridItem({
    key: `gridItem-${index}`,
    x: x,
    y: y,
    height: h,
    width: w,
    body: new VizPanel({
      title: title,
    }),
  });
}

function buildRepeatedPanel(
  index: number,
  x: number,
  y: number,
  h: number,
  w: number,
  title: string,
  length: number
): DashboardGridItem {
  const repeatedPanels = [];
  for (let i = 0; i < length; i++) {
    repeatedPanels.push(
      new VizPanel({
        key: `gridItem-${index}-clone-${i}`,
        title: `${title} - Clone ${i}`,
      })
    );
  }

  return new DashboardGridItem({
    key: `gridItem-${index}`,
    x: x,
    y: y,
    height: h,
    width: w,
    body: new VizPanel({
      title: title,
    }),
    repeatedPanels: repeatedPanels,
    maxPerRow: 2,
  });
}
