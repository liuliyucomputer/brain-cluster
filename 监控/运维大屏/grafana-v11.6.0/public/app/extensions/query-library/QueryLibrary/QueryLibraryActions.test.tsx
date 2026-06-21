import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { render } from '../../../../test/test-utils';
import { mockQueryTemplateRow } from '../utils/mocks';

import { QueryLibraryActions, QueryLibraryActionsProps } from './QueryLibraryActions';

describe('QueryLibraryActions', () => {
  const mockOnSelectQuery = jest.fn();
  const defaultProps: QueryLibraryActionsProps = {
    onSelectQuery: mockOnSelectQuery,
    selectedQueryRow: mockQueryTemplateRow
  };

  it('should render "Delete" and "Select" buttons', () => {
    render(<QueryLibraryActions {...defaultProps} />);
    expect(screen.getByRole('button', { name: 'Delete query' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Select query' })).toBeInTheDocument();
  });

  it('should call onSelectQuery when the select button is clicked', async () => {
    render(<QueryLibraryActions {...defaultProps} />);
    await userEvent.click(screen.getByRole('button', { name: 'Select query' }));
    expect(mockOnSelectQuery).toHaveBeenCalledWith(mockQueryTemplateRow.query);
  });
});
