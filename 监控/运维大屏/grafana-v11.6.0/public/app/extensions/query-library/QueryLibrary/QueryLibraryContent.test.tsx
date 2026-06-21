import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { render } from '../../../../test/test-utils';
import { mockQueryTemplateRow } from '../utils/mocks';

import { QueryLibraryContent } from './QueryLibraryContent';

describe('QueryLibraryContent', () => {
  const mockOnSelectQuery = jest.fn();

  const defaultProps = {
    onSelectQuery: mockOnSelectQuery,
    queryRows: [
      { ...mockQueryTemplateRow, uid: '1', description: 'Query 1' },
      { ...mockQueryTemplateRow, uid: '2', description: 'Query 2' },
    ],
    isFiltered: false,
  };

  it('should render list of queries', async () => {
    render(<QueryLibraryContent {...defaultProps} />);

    const radiogroup = await screen.findByRole('radiogroup');
    expect(within(radiogroup).getByText('Query 1')).toBeInTheDocument();
    expect(within(radiogroup).getByText('Query 2')).toBeInTheDocument();
  });

  it('should automatically select first query', async () => {
    render(<QueryLibraryContent {...defaultProps} />);

    expect(await screen.findByRole('radio', { name: 'Query 1' })).toBeChecked();
    expect(await screen.findByRole('radio', { name: 'Query 2' })).not.toBeChecked();
  });

  it('should show empty state when no queries are available', async () => {
    render(<QueryLibraryContent {...defaultProps} queryRows={[]} />);

    expect(await screen.findByText("You haven't saved any queries to the library yet")).toBeInTheDocument();
    expect(await screen.findByText('Start adding them from Explore or when editing a dashboard')).toBeInTheDocument();
  });

  it('should show not found state when filtered queries are empty', async () => {
    render(<QueryLibraryContent {...defaultProps} queryRows={[]} isFiltered={true} />);

    expect(await screen.findByText('No results found')).toBeInTheDocument();
    expect(await screen.findByText('Try adjusting your search or filter criteria')).toBeInTheDocument();
  });

  it('should call onSelectQuery when query is selected and action button clicked', async () => {
    render(<QueryLibraryContent {...defaultProps} />);

    await userEvent.click(await screen.findByRole('button', { name: 'Select query' }));

    expect(mockOnSelectQuery).toHaveBeenCalledWith(defaultProps.queryRows[0].query);
  });

  it('should update selected query when queryRows changes', async () => {
    const { rerender } = render(<QueryLibraryContent {...defaultProps} />);

    // Initial selection should be first query
    expect(await screen.findByRole('radio', { name: 'Query 1' })).toBeChecked();
    expect(await screen.findByRole('radio', { name: 'Query 2' })).not.toBeChecked();

    // Update queryRows to remove first query
    rerender(<QueryLibraryContent {...defaultProps} queryRows={[defaultProps.queryRows[1]]} />);

    // Selection should update to remaining query
    expect(screen.queryByRole('radio', { name: 'Query 1' })).not.toBeInTheDocument();
    expect(await screen.findByRole('radio', { name: 'Query 2' })).toBeChecked();
  });

  it('should only be able to tab to one query in the list', async () => {
    render(<QueryLibraryContent {...defaultProps} />);

    const firstItem = screen.getByRole('radio', { name: 'Query 1' });
    const secondItem = screen.getByRole('radio', { name: 'Query 2' });

    await userEvent.click(firstItem);
    expect(document.activeElement).toBe(firstItem);

    await userEvent.tab();
    expect(document.activeElement).not.toBe(firstItem);
    expect(document.activeElement).not.toBe(secondItem);

    await userEvent.tab({ shift: true });
    expect(document.activeElement).toBe(firstItem);
    expect(document.activeElement).not.toBe(secondItem);

    await userEvent.tab({ shift: true });
    expect(document.activeElement).not.toBe(firstItem);
    expect(document.activeElement).not.toBe(secondItem);
  });

  it('should be able to navigate through the list with arrow keys', async () => {
    render(<QueryLibraryContent {...defaultProps} />);

    const firstItem = screen.getByRole('radio', { name: 'Query 1' });
    const secondItem = screen.getByRole('radio', { name: 'Query 2' });

    await userEvent.click(firstItem);
    expect(document.activeElement).toBe(firstItem);

    await userEvent.keyboard('{arrowdown}');
    expect(document.activeElement).not.toBe(firstItem);
    expect(document.activeElement).toBe(secondItem);

    await userEvent.keyboard('{arrowdown}');
    expect(document.activeElement).toBe(firstItem);
    expect(document.activeElement).not.toBe(secondItem);

    await userEvent.keyboard('{arrowup}');
    expect(document.activeElement).not.toBe(firstItem);
    expect(document.activeElement).toBe(secondItem);

    await userEvent.keyboard('{arrowup}');
    expect(document.activeElement).toBe(firstItem);
    expect(document.activeElement).not.toBe(secondItem);
  });
});
