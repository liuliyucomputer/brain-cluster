import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render } from 'test/test-utils';

import { defaultTimeRange } from 'app/extensions/reports/state/reducers';

import ReportForm from '../ReportForm';

jest.mock('app/core/core', () => {
  return {
    contextSrv: {
      hasPermission: () => true,
    },
  };
});

function setup(jsx: JSX.Element) {
  return {
    ...render(jsx),
    user: userEvent.setup(),
  };
}

describe('EmailConfiguration', () => {
  it('should render', async () => {
    const { user } = setup(
      <ReportForm
        report={{
          name: 'Report name test',
          dashboards: [{ dashboard: { name: 'Test dashboard', uid: '1' }, timeRange: defaultTimeRange.raw }],
        }}
      />
    );

    const emailConfigurationSection = screen.getByRole('button', { name: /email settings/i });
    expect(emailConfigurationSection).toBeInTheDocument();

    await user.click(emailConfigurationSection);

    expect(await screen.findByRole('textbox', { name: /email subject/i })).toBeInTheDocument();
    expect(await screen.findByRole('textbox', { name: /message/i })).toBeInTheDocument();
    expect(await screen.findByRole('textbox', { name: /reply-to-email address/i })).toBeInTheDocument();
    expect(await screen.findByRole('checkbox', { name: /include dashboard link/i })).toBeInTheDocument();
    expect(await screen.findByRole('checkbox', { name: /embed dashboard image/i })).toBeInTheDocument();
  });
  it('should disable submit button when replyTo email is invalid but should be enabled when it is valid or empty', async () => {
    const { user } = setup(
      <ReportForm
        report={{
          name: 'Report name test',
          dashboards: [{ dashboard: { name: 'Test dashboard', uid: '1' }, timeRange: defaultTimeRange }],
        }}
      />
    );

    const emailConfigurationSection = screen.getByRole('button', { name: /email settings/i });
    await user.click(emailConfigurationSection);

    const submitButton = await screen.findByRole('button', { name: /schedule report/i });
    expect(submitButton).toBeEnabled();

    const replyToInput = await screen.findByRole('textbox', { name: /reply-to-email address/i });
    await user.type(replyToInput, 'invalid-email');

    await waitFor(() => {
      expect(submitButton).toBeDisabled();
      expect(screen.getByText('Invalid email')).toBeInTheDocument();
    });

    await user.clear(replyToInput);
    await waitFor(() => {
      expect(submitButton).toBeEnabled();
    });

    await user.type(replyToInput, 'valid@email.com');
    await waitFor(() => {
      expect(submitButton).toBeEnabled();
      expect(screen.queryByText('Invalid email')).not.toBeInTheDocument();
    });
  });
});
