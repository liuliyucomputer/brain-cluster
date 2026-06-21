import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { render } from '../../../../test/test-utils';
import { mockQueryTemplateRow } from '../utils/mocks';

import { QueryLibraryDetails } from './QueryLibraryDetails';

jest.mock('@grafana/runtime', () => ({
  ...jest.requireActual('@grafana/runtime'),
  getDataSourceSrv: () => ({
    get: () => ({
      meta: {
        info: {
          logos: {
            small: 'public/img/icn-prometheus.svg'
          }
        },
      },
      type: 'prometheus'
    })
  })
}));

// Mock the analytics event
jest.mock('../QueryLibraryAnalyticsEvents', () => ({
  queryLibraryTrackAddOrEditDescription: jest.fn(),
}));

describe('QueryLibraryDetails', () => {
  it('should render datasource logo and query description', async () => {
    render(<QueryLibraryDetails query={mockQueryTemplateRow} />);

    const logo = await screen.findByRole('img', { name: 'prometheus' });
    expect(logo).toHaveAttribute('src', 'public/img/icn-prometheus.svg');

    const description = await screen.findByText(mockQueryTemplateRow.description!);
    expect(description).toBeInTheDocument();
  });

  it('should render other query details', async () => {
    render(<QueryLibraryDetails query={mockQueryTemplateRow} />);

    const query = await screen.findByText(mockQueryTemplateRow.queryText!);
    expect(query).toBeInTheDocument();
    expect(await screen.findByLabelText('Datasource')).toHaveValue(mockQueryTemplateRow.datasourceName);
    expect(await screen.findByLabelText('Author')).toHaveValue(mockQueryTemplateRow.user?.displayName);
  });

  it('should open edit modal when clicking edit button', async () => {
    render(<QueryLibraryDetails query={mockQueryTemplateRow} />);

    const editButton = await screen.findByRole('button', { name: 'Edit query' });
    await userEvent.click(editButton);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Edit query' })).toBeInTheDocument();
  });
});
